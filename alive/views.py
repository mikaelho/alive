"""Generic LiveViews for Alive models."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Type
import uuid

from django.db import models
from pyview import LiveView, LiveViewSocket, is_connected
from pyview.events import InfoEvent
from pyview.template import template_file, LiveRender
from pyview.meta import PyViewMeta

from .mixin import AliveMixin
from .store import get_store, DjangoDataStore
from .components import EditableFieldMixin, ItemMixin, render_item_data

# Path to the default template
TEMPLATE_DIR = Path(__file__).parent / "templates"
DEFAULT_TEMPLATE = template_file(str(TEMPLATE_DIR / "items.html"))
INDEX_TEMPLATE = template_file(str(TEMPLATE_DIR / "index.html"))


@dataclass
class IndexContext:
    """Context for the index page."""

    items: list[dict] = field(default_factory=list)


@dataclass
class ModelContext:
    """Generic context for model views."""

    items: list[dict] = field(default_factory=list)
    session_id: str = ""
    editing: dict[str, str] = field(default_factory=dict)
    model_name: str = ""
    model_name_singular: str = ""
    field_names: list[str] = field(default_factory=list)
    title_field: str = ""
    content_fields: list[str] = field(default_factory=list)
    filters: dict[str, str] = field(default_factory=dict)
    # Breadcrumb navigation: list of {"label": str, "url": str or None}
    breadcrumbs: list[dict] = field(default_factory=list)
    # Creation state
    creating: bool = False
    create_fields: list[dict] = field(default_factory=list)
    create_values: dict[str, str] = field(default_factory=dict)
    create_error: str = ""
    # Picker state for adding existing items to relationships
    picker_open: bool = False
    picker_items: list[dict] = field(default_factory=list)
    picker_selected: list[str] = field(default_factory=list)
    picker_has_selection: bool = False  # Helper for template
    picker_relation: str = ""  # The relation field name (e.g., "recipes")
    picker_related_pk: str = ""  # The PK of the related object


def create_model_liveview(model: Type[models.Model], url_prefix: str = "/alive") -> Type[LiveView]:
    """
    Factory function to create a LiveView class for a Django model.

    Args:
        model: The Django model class (must have AliveMixin)
        url_prefix: URL prefix for alive routes (for building dive links)

    Returns:
        A LiveView class configured for that model
    """
    if not issubclass(model, AliveMixin):
        raise ValueError(f"Model {model} must use AliveMixin")

    store = get_store(model)
    conf = model.get_alive_conf()
    fields = list(conf.fields) if conf.fields else model.get_field_names()
    title_field = conf.get_title_field(fields)
    content_fields = [f for f in fields if f != title_field]
    model_name = model._meta.model_name
    model_display_name = model._meta.verbose_name_plural.title()
    model_display_name_singular = model._meta.verbose_name.title()
    dive_relations = model.get_dive_relations(url_prefix)
    create_fields = model.get_creatable_fields()

    class GeneratedModelLiveView(EditableFieldMixin, ItemMixin, LiveView[ModelContext]):
        """Auto-generated LiveView for a model."""

        # Store references for mixins
        lock_manager = store
        data_store = store

        async def render(self, context: ModelContext, meta: PyViewMeta):
            """Render using the default alive template."""
            return LiveRender(DEFAULT_TEMPLATE, context, meta)

        async def mount(self, socket: LiveViewSocket[ModelContext], session: dict[str, Any]):
            session_id = session.get("id")
            if not session_id:
                session_id = str(uuid.uuid4())
                session["id"] = session_id

            editing: dict[str, str] = {}

            # Content fields are all fields except the title field
            content_field_list = [f for f in fields if f != title_field]

            # Initialize with empty filters - handle_params will set them
            socket.context = ModelContext(
                items=[],
                session_id=session_id,
                editing=editing,
                model_name=model_display_name,
                model_name_singular=model_display_name_singular,
                field_names=list(fields),
                title_field=title_field or "",
                content_fields=content_field_list,
                filters={},
                breadcrumbs=[],
            )

            if is_connected(socket):
                await socket.subscribe(store.channel)

        async def handle_params(self, url, params: dict, socket: LiveViewSocket[ModelContext]):
            """Handle URL parameters for filtering."""
            # Parse filter params from query string
            filters = {}

            # Build breadcrumbs
            breadcrumbs = [
                {"label": "Home", "url": f"{url_prefix}/"},
            ]

            for param, values in params.items():
                # params values are lists from parse_qs
                value = values[0] if isinstance(values, list) and values else values
                if value:
                    # Convert to ORM filter (e.g., recipes -> recipes__pk)
                    filters[f"{param}__pk"] = value

                    # Add parent model to breadcrumbs
                    parent_url = self._get_back_url(param, value)
                    parent_model_name = self._get_related_model_name(param)
                    if parent_url and parent_model_name:
                        breadcrumbs.append({"label": parent_model_name, "url": parent_url})

                    # Add the specific parent item
                    related_name = await self._get_related_object_name(param, value)
                    if related_name:
                        breadcrumbs.append({"label": related_name, "url": None})

            # Current model (no link - we're here)
            breadcrumbs.append({"label": model_display_name, "url": None if filters else None})

            socket.context.filters = filters
            socket.context.breadcrumbs = breadcrumbs

            # Now load the items with filters
            socket.context.items = await self._build_items_data(
                socket.context.session_id, socket.context.editing, filters
            )

        async def _get_related_object_name(self, relation_field: str, pk: str) -> str | None:
            """Get the string representation of a related object."""
            from asgiref.sync import sync_to_async

            try:
                # Find the related model from the relation field
                for field in model._meta.get_fields():
                    if field.name == relation_field:
                        if hasattr(field, 'related_model'):
                            related_model = field.related_model

                            @sync_to_async(thread_sensitive=False)
                            def get_obj():
                                return related_model.objects.get(pk=pk)

                            obj = await get_obj()
                            return str(obj)
            except Exception:
                pass
            return None

        def _get_back_url(self, relation_field: str, pk: str) -> str:
            """Build URL to go back to the related object's list."""
            # Find the related model and build its URL
            for field in model._meta.get_fields():
                if field.name == relation_field:
                    if hasattr(field, 'related_model'):
                        related_model = field.related_model
                        related_model_name = related_model._meta.model_name
                        return f"{url_prefix}/{related_model_name}/"
            return ""

        def _get_related_model_name(self, relation_field: str) -> str:
            """Get the plural display name of a related model."""
            for field in model._meta.get_fields():
                if field.name == relation_field:
                    if hasattr(field, 'related_model'):
                        return field.related_model._meta.verbose_name_plural.title()
            return ""

        async def disconnect(self, socket: LiveViewSocket[ModelContext]):
            """Clean up locks when client disconnects."""
            session_id = socket.context.session_id
            released = store.release_all_locks(session_id)

            if released:
                await socket.broadcast(store.channel, {
                    "action": "locks_released",
                    "keys": [f"{item_id}:{field_name}" for item_id, field_name in released],
                })

        async def handle_event(self, event: str, payload: dict[str, Any], socket: LiveViewSocket[ModelContext]):
            # Handle creation events
            if event == "start_create":
                socket.context.creating = True
                socket.context.create_fields = [
                    {**f, "value": "", "autofocus": i == 0} for i, f in enumerate(create_fields)
                ]
                socket.context.create_values = {}
                socket.context.create_error = ""
                return

            if event == "cancel_create":
                socket.context.creating = False
                socket.context.create_values = {}
                socket.context.create_error = ""
                return

            if event == "update_create_field":
                field_name = payload.get("field", "")
                value = payload.get("value", "")
                socket.context.create_values[field_name] = value
                # Update the value in create_fields for template rendering
                for f in socket.context.create_fields:
                    if f["name"] == field_name:
                        f["value"] = value
                        break
                return

            if event == "save_create":
                # Validate required fields
                missing = []
                for f in create_fields:
                    if f["required"] and not socket.context.create_values.get(f["name"]):
                        missing.append(f["label"])

                if missing:
                    socket.context.create_error = f"Required: {', '.join(missing)}"
                    return

                # Create the item
                item = await store.create_item(socket.context.create_values)
                if not item:
                    socket.context.create_error = "Failed to create item"
                    return

                # If we have a filter (from diving), add to that relation
                if socket.context.filters:
                    for param, value in socket.context.filters.items():
                        # param is like "recipes__pk", we need "recipes"
                        relation_field = param.replace("__pk", "")
                        await store.add_to_relation(item, relation_field, value)

                # Reset creation state
                socket.context.creating = False
                socket.context.create_values = {}
                socket.context.create_error = ""

                # Refresh the list
                await self._refresh_view_async(socket)
                await self._broadcast_change(socket)
                return

            if event == "delete_item":
                item_id = payload.get("item_id", "")
                if item_id:
                    # Release any locks on this item
                    store.release_all_locks(socket.context.session_id)

                    # Delete the item
                    success = await store.delete_item(item_id)
                    if success:
                        await self._refresh_view_async(socket)
                        await socket.broadcast(store.channel, {"action": "item_deleted"})
                return

            if event == "unlink_item":
                item_id = payload.get("item_id", "")
                if item_id and socket.context.filters:
                    # Get the relation info from filters
                    for param, value in socket.context.filters.items():
                        relation_field = param.replace("__pk", "")
                        success = await store.remove_from_relation(item_id, relation_field, value)
                        if success:
                            await self._refresh_view_async(socket)
                            await self._broadcast_change(socket)
                        break
                return

            # Picker events for adding existing items to relationships
            if event == "open_picker":
                # Only works when we have a filter (viewing related items)
                if socket.context.filters:
                    for param, value in socket.context.filters.items():
                        relation_field = param.replace("__pk", "")
                        # Get items not already linked
                        unlinked = await store.get_unlinked_items(relation_field, value)
                        socket.context.picker_items = [
                            {"id": str(item.pk), "title": str(item), "selected": False}
                            for item in unlinked
                        ]
                        socket.context.picker_open = True
                        socket.context.picker_selected = []
                        socket.context.picker_relation = relation_field
                        socket.context.picker_related_pk = value
                        break
                return

            if event == "close_picker":
                socket.context.picker_open = False
                socket.context.picker_items = []
                socket.context.picker_selected = []
                socket.context.picker_has_selection = False
                return

            if event == "toggle_picker_item":
                item_id = payload.get("item_id", "")
                if item_id:
                    if item_id in socket.context.picker_selected:
                        socket.context.picker_selected.remove(item_id)
                    else:
                        socket.context.picker_selected.append(item_id)
                    # Update the picker_items to reflect selection state
                    for item in socket.context.picker_items:
                        item["selected"] = item["id"] in socket.context.picker_selected
                    # Update helper boolean
                    socket.context.picker_has_selection = len(socket.context.picker_selected) > 0
                return

            if event == "confirm_picker":
                if socket.context.picker_selected and socket.context.picker_relation:
                    await store.add_items_to_relation(
                        socket.context.picker_selected,
                        socket.context.picker_relation,
                        socket.context.picker_related_pk
                    )
                    # Reset picker state
                    socket.context.picker_open = False
                    socket.context.picker_items = []
                    socket.context.picker_selected = []
                    socket.context.picker_has_selection = False
                    # Refresh the list
                    await self._refresh_view_async(socket)
                    await self._broadcast_change(socket)
                return

            # Try field events first
            if await self.handle_field_event(event, payload, socket):
                return

            # Try item events
            if await self.handle_item_event(event, payload, socket):
                return

        async def handle_info(self, event: InfoEvent, socket: LiveViewSocket[ModelContext]):
            """Handle pub/sub messages from other clients or Django signals."""
            if event.name != store.channel:
                return

            data = event.payload
            action = data.get("action", "")

            if action in ("state_changed", "locks_released", "item_created", "item_deleted"):
                await self._refresh_view_async(socket)
            elif action == "conflict":
                conflict_key = data.get("key", "")
                if conflict_key in socket.context.editing:
                    del socket.context.editing[conflict_key]
                await self._refresh_view_async(socket)

        def _refresh_view(self, socket: LiveViewSocket[ModelContext]):
            """Sync refresh - schedules async refresh."""
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._refresh_view_async(socket))
            except RuntimeError:
                pass

        async def _refresh_view_async(self, socket: LiveViewSocket[ModelContext]):
            """Async refresh the items data in context."""
            socket.context.items = await self._build_items_data(
                socket.context.session_id, socket.context.editing, socket.context.filters
            )

        async def _broadcast_change(self, socket: LiveViewSocket[ModelContext]):
            """Broadcast state change to other clients."""
            await socket.broadcast(store.channel, {"action": "state_changed"})

        async def _build_items_data(self, session_id: str, editing: dict[str, str], filters: dict | None = None) -> list[dict]:
            """Build the items data for the template."""
            items = await store.get_items(filters)
            result = []
            for item in items:
                item_data = render_item_data(item, fields, session_id, editing, store, title_field, content_fields)
                # Add dive buttons
                item_data["dive_buttons"] = [
                    {
                        "label": rel["label"],
                        "url": f"{rel['target_url']}?{rel['filter_param']}={item.pk}",
                    }
                    for rel in dive_relations
                    if rel["filter_param"]  # Only include if we can filter
                ]
                result.append(item_data)
            return result

    # Set a meaningful name for debugging
    GeneratedModelLiveView.__name__ = f"{model.__name__}LiveView"
    GeneratedModelLiveView.__qualname__ = f"{model.__name__}LiveView"

    return GeneratedModelLiveView


def create_index_liveview(models_info: list[dict]) -> Type[LiveView]:
    """
    Factory function to create an index LiveView listing all registered models.

    Args:
        models_info: List of dicts with 'title', 'description', 'url' for each model

    Returns:
        A LiveView class for the index page
    """

    class IndexLiveView(LiveView[IndexContext]):
        """Index page listing all available model views."""

        async def render(self, context: IndexContext, meta: PyViewMeta):
            """Render using the index template."""
            return LiveRender(INDEX_TEMPLATE, context, meta)

        async def mount(self, socket: LiveViewSocket[IndexContext], session: dict[str, Any]):
            socket.context = IndexContext(items=models_info)

    return IndexLiveView
