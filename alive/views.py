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
from .store import get_store, DjangoDataStore, acquire_lock, release_lock, get_lock_holder
from .components import EditableFieldMixin, ItemMixin, render_item_data
from .components.editable_field import render_markdown_safe

# Path to the default template
TEMPLATE_DIR = Path(__file__).parent / "templates"
DEFAULT_TEMPLATE_PATH = str(TEMPLATE_DIR / "items.html")
GRID_TEMPLATE_PATH = str(TEMPLATE_DIR / "grid.html")
INDEX_TEMPLATE_PATH = str(TEMPLATE_DIR / "index.html")


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
    # FK picker state
    fk_picker_open: bool = False
    fk_picker_field: str = ""  # Field name being edited
    fk_picker_item_id: str = ""  # Item whose FK is being edited
    fk_picker_items: list[dict] = field(default_factory=list)  # Available choices
    fk_picker_filter: str = ""  # Current search filter
    fk_picker_current: str = ""  # Current FK value ID (for highlighting)
    fk_picker_nullable: bool = False  # Whether None is allowed
    # Tag picker state
    tag_picker_open: bool = False
    tag_picker_field: str = ""
    tag_picker_item_id: str = ""
    tag_picker_label: str = ""
    tag_picker_items: list[dict] = field(default_factory=list)
    tag_picker_filter: str = ""
    tag_picker_can_create: bool = False
    tag_picker_multiple: bool = True
    tag_picker_scope_model_label: str = ""
    tag_picker_scope_pk: str = ""
    tag_picker_scope_m2m_field: str = ""
    tag_create_open: bool = False
    tag_create_fields: list[dict] = field(default_factory=list)
    tag_create_values: dict = field(default_factory=dict)
    tag_create_error: str = ""
    # Tag field configs for template
    tag_field_configs: list[dict] = field(default_factory=list)
    # Inline create modal state
    inline_create_open: bool = False
    inline_create_relation: str = ""
    inline_create_item_id: str = ""
    inline_create_target_fields: list[dict] = field(default_factory=list)
    inline_create_through_fields: list[dict] = field(default_factory=list)
    inline_create_target_values: dict = field(default_factory=dict)
    inline_create_through_values: dict = field(default_factory=dict)
    inline_create_error: str = ""
    # Current player ID from session (for visibility filtering)
    player_id: int | None = None
    # Grid/detail view mode
    view_mode: str = "detail"
    detail_item_id: str = ""
    list_fields: list[str] = field(default_factory=list)


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
    fk_fields = model.get_fk_fields()
    fk_field_names = [f["name"] for f in fk_fields]
    compact_field_names = list(conf.compact_fields) if conf.compact_fields else []

    # Resolve tag field configurations at factory time
    tag_confs = model.get_tag_fields_conf()
    tag_configs_resolved = []
    for tc in tag_confs:
        scope_info = model.resolve_tag_scope(tc)
        model_info = store.get_tag_model_info(tc.field_name)
        tag_configs_resolved.append({
            "conf": tc,
            "scope": scope_info,
            "model_info": model_info,
            "label": tc.label or tc.field_name.replace("_", " ").title(),
        })
    has_tag_fields = bool(tag_configs_resolved)

    # Pre-compute inline relation info
    inline_infos = model.get_inline_info()
    inline_info_by_name = {info["relation_name"]: info for info in inline_infos}
    has_inline = bool(inline_infos)

    # Pre-resolve tag field scopes for through models
    inline_tag_scopes = {}  # {(relation_name, field_name): scope_info}
    for info in inline_infos:
        through_model = info["through_model"]
        if hasattr(through_model, 'get_tag_fields_conf'):
            for tc in through_model.get_tag_fields_conf():
                scope_info = through_model.resolve_tag_scope(tc)
                inline_tag_scopes[(info["relation_name"], tc.field_name)] = {
                    "scope": scope_info,
                    "link_fk": info["link_fk"],
                }

    async def _resolve_inline_tag_choices(through_model, link_fk, parent_item_id):
        """Resolve scoped tag choices for a through model's tag fields."""
        from asgiref.sync import sync_to_async
        result = {}
        if not hasattr(through_model, 'get_tag_fields_conf'):
            return result
        for tc in through_model.get_tag_fields_conf():
            scope_info = through_model.resolve_tag_scope(tc)
            if not scope_info:
                continue
            scope_parts = scope_info["scope_path_parts"]
            scope_m2m = scope_info["scope_m2m_field"]
            remaining = scope_parts[1:] if scope_parts[0] == link_fk else scope_parts

            @sync_to_async(thread_sensitive=False)
            def _fetch(remaining=remaining, scope_m2m=scope_m2m):
                obj = model.objects.get(pk=int(parent_item_id))
                for part in remaining:
                    obj = getattr(obj, part)
                return [(str(tag.pk), str(tag)) for tag in getattr(obj, scope_m2m).all()]

            result[tc.field_name] = await _fetch()
        return result

    class GeneratedModelLiveView(EditableFieldMixin, ItemMixin, LiveView[ModelContext]):
        """Auto-generated LiveView for a model."""

        # Store references for mixins
        lock_manager = store
        data_store = store

        async def render(self, context: ModelContext, meta: PyViewMeta):
            """Render using the appropriate template based on view mode."""
            if context.view_mode == "grid":
                return LiveRender(template_file(GRID_TEMPLATE_PATH), context, meta)
            return LiveRender(template_file(DEFAULT_TEMPLATE_PATH), context, meta)

        async def mount(self, socket: LiveViewSocket[ModelContext], session: dict[str, Any]):
            # Generate a unique ID per socket/tab for edit locking
            session_id = str(uuid.uuid4())

            player_id = session.get("player_id")
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
                player_id=player_id,
            )

            if is_connected(socket):
                await socket.subscribe(store.channel)
                # Subscribe to inline target model channels for cross-view lock updates
                for info in inline_infos:
                    target_store = get_store(info["target_model"])
                    if target_store.channel != store.channel:
                        await socket.subscribe(target_store.channel)

        async def handle_params(self, url, params: dict, socket: LiveViewSocket[ModelContext]):
            """Handle URL parameters for filtering."""
            # Parse filter params from query string
            filters = {}
            detail_id = None

            # Build breadcrumbs
            breadcrumbs = [
                {"label": "Home", "url": f"{url_prefix}/"},
            ]

            for param, values in params.items():
                # params values are lists from parse_qs
                value = values[0] if isinstance(values, list) and values else values
                if not value:
                    continue

                if param == "detail":
                    detail_id = value
                    continue

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

            # Determine view mode: grid if list_fields configured, no detail param, no relation filters
            if conf.list_fields and not detail_id and not filters:
                socket.context.view_mode = "grid"
                socket.context.list_fields = list(conf.list_fields)
                socket.context.detail_item_id = ""
                breadcrumbs.append({"label": model_display_name, "url": None})
                socket.context.filters = {}
                socket.context.breadcrumbs = breadcrumbs
                socket.context.items = await self._build_grid_data(
                    player_id=socket.context.player_id,
                )
            else:
                socket.context.view_mode = "detail"
                if detail_id:
                    filters["pk"] = detail_id
                    socket.context.detail_item_id = detail_id
                    # Add breadcrumb back to grid
                    grid_url = f"{url_prefix}/{model_name}/"
                    breadcrumbs.append({"label": model_display_name, "url": grid_url})
                    # Add item name as final breadcrumb
                    item_name = await self._get_item_name(detail_id)
                    if item_name:
                        breadcrumbs.append({"label": item_name, "url": None})
                else:
                    socket.context.detail_item_id = ""
                    breadcrumbs.append({"label": model_display_name, "url": None})

                socket.context.filters = filters
                socket.context.breadcrumbs = breadcrumbs
                socket.context.items = await self._build_items_data(
                    socket.context.session_id, socket.context.editing, filters,
                    player_id=socket.context.player_id,
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

        async def _get_item_name(self, item_id: str) -> str | None:
            """Get the string representation of an item by its ID."""
            item = await store.get_item_by_id(item_id)
            return str(item) if item else None

        async def disconnect(self, socket: LiveViewSocket[ModelContext]):
            """Clean up locks when client disconnects."""
            session_id = socket.context.session_id
            released = release_all_locks(session_id)

            if released:
                # Group released locks by model and broadcast to each affected channel
                affected_channels = set()
                for label, item_id, field_name in released:
                    affected_channels.add(f"alive:{label}")
                for channel in affected_channels:
                    await socket.broadcast(channel, {"action": "locks_released"})

        async def handle_event(self, event: str, payload: dict[str, Any], socket: LiveViewSocket[ModelContext]):
            # Grid navigation events
            if event == "grid_navigate":
                item_id = payload.get("id", "")
                if item_id:
                    base = f"{url_prefix}/{model_name}/"
                    await socket.push_navigate(base, {"detail": item_id})
                return

            if event == "grid_back":
                base = f"{url_prefix}/{model_name}/"
                await socket.push_navigate(base)
                return

            # Handle creation events
            if event == "start_create":
                socket.context.creating = True
                # Build create fields, loading FK choices dynamically
                fields_with_choices = []
                for i, f in enumerate(create_fields):
                    field_data = {**f, "value": "", "autofocus": i == 0}
                    if f.get("field_type") == "fk":
                        # Load FK choices now (async-safe)
                        choices = await store.get_fk_choices_for_create(f["name"])
                        field_data["choices"] = choices
                        field_data["field_type"] = "select"  # Render as select
                    fields_with_choices.append(field_data)
                socket.context.create_fields = fields_with_choices
                socket.context.create_values = {}
                socket.context.create_error = ""
                return

            if event == "cancel_create":
                socket.context.creating = False
                socket.context.create_values = {}
                socket.context.create_error = ""
                return

            if event == "update_create_field":
                # Form phx-change sends all form values keyed by name.
                # Values may arrive as lists; unwrap single-element lists.
                for f in socket.context.create_fields:
                    name = f["name"]
                    if name in payload:
                        value = payload[name]
                        if isinstance(value, list) and len(value) == 1:
                            value = value[0]
                        f["value"] = value
                        socket.context.create_values[name] = value
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

            # FK picker events
            if event == "open_fk_picker":
                item_id = payload.get("item_id", "")
                field_name = payload.get("field", "")
                if item_id and field_name:
                    # Get FK field info
                    fk_info = store.get_fk_field_info(field_name)
                    if fk_info:
                        # Get current FK value pk
                        current_value = await store.get_field_value(item_id, field_name)
                        current_pk = ""
                        if current_value is not None and hasattr(current_value, 'pk'):
                            current_pk = str(current_value.pk)

                        # Get available choices
                        choices = await store.get_fk_choices(field_name, "")

                        socket.context.fk_picker_open = True
                        socket.context.fk_picker_field = field_name
                        socket.context.fk_picker_item_id = item_id
                        socket.context.fk_picker_items = choices
                        socket.context.fk_picker_filter = ""
                        socket.context.fk_picker_current = current_pk
                        socket.context.fk_picker_nullable = fk_info["nullable"]
                return

            if event == "close_fk_picker":
                socket.context.fk_picker_open = False
                socket.context.fk_picker_field = ""
                socket.context.fk_picker_item_id = ""
                socket.context.fk_picker_items = []
                socket.context.fk_picker_filter = ""
                socket.context.fk_picker_current = ""
                socket.context.fk_picker_nullable = False
                return

            if event == "filter_fk_picker":
                filter_text = payload.get("value", "")
                if isinstance(filter_text, list):
                    filter_text = filter_text[0] if filter_text else ""
                socket.context.fk_picker_filter = filter_text
                # Re-fetch choices with filter
                if socket.context.fk_picker_field:
                    choices = await store.get_fk_choices(socket.context.fk_picker_field, filter_text)
                    socket.context.fk_picker_items = choices
                return

            if event == "select_fk_item":
                pk = payload.get("pk", "")
                if socket.context.fk_picker_item_id and socket.context.fk_picker_field:
                    # Set the FK value
                    related_pk = pk if pk else None
                    success = await store.set_fk_value(
                        socket.context.fk_picker_item_id,
                        socket.context.fk_picker_field,
                        related_pk
                    )
                    if success:
                        # Reset picker state
                        socket.context.fk_picker_open = False
                        socket.context.fk_picker_field = ""
                        socket.context.fk_picker_item_id = ""
                        socket.context.fk_picker_items = []
                        socket.context.fk_picker_filter = ""
                        socket.context.fk_picker_current = ""
                        socket.context.fk_picker_nullable = False
                        # Refresh the list
                        await self._refresh_view_async(socket)
                        await self._broadcast_change(socket)
                return

            # Tag picker events
            if event == "open_tag_picker":
                item_id = payload.get("item_id", "")
                field_name = payload.get("field", "")
                if item_id and field_name:
                    # Find the resolved config for this field
                    tc_info = next((t for t in tag_configs_resolved if t["conf"].field_name == field_name), None)
                    if tc_info:
                        tc = tc_info["conf"]
                        scope = tc_info["scope"]
                        scope_model = None
                        scope_pk = None
                        scope_m2m_field = None
                        scope_model_label = ""

                        if scope:
                            # Resolve scope pk from the item by walking scope_path_parts
                            from asgiref.sync import sync_to_async

                            @sync_to_async(thread_sensitive=False)
                            def resolve_scope_pk():
                                obj = self.data_store.model.objects.get(pk=int(item_id))
                                for part in scope["scope_path_parts"]:
                                    obj = getattr(obj, part)
                                return str(obj.pk)

                            try:
                                scope_pk = await resolve_scope_pk()
                                scope_model = scope["scope_model"]
                                scope_m2m_field = scope["scope_m2m_field"]
                                scope_model_label = scope_model._meta.label
                            except Exception:
                                scope_pk = None

                        available = await store.get_available_tags(
                            item_id, field_name,
                            scope_model, scope_pk, scope_m2m_field, "",
                        )

                        multiple = tc_info["model_info"]["multiple"] if tc_info["model_info"] else True

                        socket.context.tag_picker_open = True
                        socket.context.tag_picker_field = field_name
                        socket.context.tag_picker_item_id = item_id
                        socket.context.tag_picker_label = tc_info["label"]
                        socket.context.tag_picker_items = available
                        socket.context.tag_picker_filter = ""
                        socket.context.tag_picker_can_create = False
                        socket.context.tag_picker_multiple = multiple
                        socket.context.tag_picker_scope_model_label = scope_model_label
                        socket.context.tag_picker_scope_pk = scope_pk or ""
                        socket.context.tag_picker_scope_m2m_field = scope_m2m_field or ""
                        socket.context.tag_create_open = False
                        socket.context.tag_create_fields = []
                        socket.context.tag_create_values = {}
                        socket.context.tag_create_error = ""
                return

            if event == "close_tag_picker":
                socket.context.tag_picker_open = False
                socket.context.tag_picker_field = ""
                socket.context.tag_picker_item_id = ""
                socket.context.tag_picker_label = ""
                socket.context.tag_picker_items = []
                socket.context.tag_picker_filter = ""
                socket.context.tag_picker_can_create = False
                socket.context.tag_picker_multiple = True
                socket.context.tag_picker_scope_model_label = ""
                socket.context.tag_picker_scope_pk = ""
                socket.context.tag_picker_scope_m2m_field = ""
                socket.context.tag_create_open = False
                socket.context.tag_create_fields = []
                socket.context.tag_create_values = {}
                socket.context.tag_create_error = ""
                return

            if event == "filter_tag_picker":
                search_text = payload.get("value", "")
                if isinstance(search_text, list):
                    search_text = search_text[0] if search_text else ""
                socket.context.tag_picker_filter = search_text

                # Reconstruct scope model from label if needed
                scope_model = None
                scope_pk = socket.context.tag_picker_scope_pk or None
                scope_m2m_field = socket.context.tag_picker_scope_m2m_field or None
                if socket.context.tag_picker_scope_model_label:
                    from django.apps import apps
                    scope_model = apps.get_model(socket.context.tag_picker_scope_model_label)

                available = await store.get_available_tags(
                    socket.context.tag_picker_item_id,
                    socket.context.tag_picker_field,
                    scope_model, scope_pk, scope_m2m_field, search_text,
                )
                socket.context.tag_picker_items = available

                # Can create if search text has no exact match
                exact_match = any(t["title"].lower() == search_text.lower() for t in available) if search_text else True
                socket.context.tag_picker_can_create = bool(search_text) and not exact_match
                return

            if event == "toggle_tag":
                tag_pk = payload.get("tag_pk", "")
                if tag_pk and socket.context.tag_picker_item_id and socket.context.tag_picker_field:
                    await store.toggle_tag(
                        socket.context.tag_picker_item_id,
                        socket.context.tag_picker_field,
                        tag_pk,
                    )
                    # Refresh picker items
                    scope_model = None
                    scope_pk = socket.context.tag_picker_scope_pk or None
                    scope_m2m_field = socket.context.tag_picker_scope_m2m_field or None
                    if socket.context.tag_picker_scope_model_label:
                        from django.apps import apps
                        scope_model = apps.get_model(socket.context.tag_picker_scope_model_label)

                    # Refresh items list
                    await self._refresh_view_async(socket)
                    await self._broadcast_change(socket)

                    if not socket.context.tag_picker_multiple:
                        # Single-select: close picker after selection
                        socket.context.tag_picker_open = False
                        socket.context.tag_picker_field = ""
                        socket.context.tag_picker_item_id = ""
                        socket.context.tag_picker_label = ""
                        socket.context.tag_picker_items = []
                        socket.context.tag_picker_filter = ""
                        socket.context.tag_picker_can_create = False
                        socket.context.tag_picker_multiple = True
                        socket.context.tag_picker_scope_model_label = ""
                        socket.context.tag_picker_scope_pk = ""
                        socket.context.tag_picker_scope_m2m_field = ""
                        socket.context.tag_create_open = False
                        socket.context.tag_create_fields = []
                        socket.context.tag_create_values = {}
                        socket.context.tag_create_error = ""
                    else:
                        # Multi-select: refresh picker items to show updated state
                        available = await store.get_available_tags(
                            socket.context.tag_picker_item_id,
                            socket.context.tag_picker_field,
                            scope_model, scope_pk, scope_m2m_field,
                            socket.context.tag_picker_filter,
                        )
                        socket.context.tag_picker_items = available
                return

            if event == "remove_tag":
                item_id = payload.get("item_id", "")
                tag_pk = payload.get("tag_pk", "")
                field_name = payload.get("field", "")
                if item_id and tag_pk and field_name:
                    await store.remove_tag(item_id, field_name, tag_pk)
                    await self._refresh_view_async(socket)
                    await self._broadcast_change(socket)
                return

            if event == "reorder_tag":
                item_id = payload.get("item_id", "")
                field_name = payload.get("field", "")
                tag_pk = payload.get("tag_pk", "")
                position = payload.get("position", "0")
                if item_id and field_name and tag_pk:
                    await store.reorder_tag(item_id, field_name, tag_pk, int(position))
                    await self._refresh_view_async(socket)
                    await self._broadcast_change(socket)
                return

            if event == "start_tag_create":
                field_name = socket.context.tag_picker_field
                tc_info = next((t for t in tag_configs_resolved if t["conf"].field_name == field_name), None)
                if tc_info and tc_info["model_info"]:
                    model_info = tc_info["model_info"]
                    if model_info["simple"]:
                        # Simple model - create immediately with search text as title
                        title_field_name = model_info["title_field"]
                        if title_field_name:
                            scope_model = None
                            scope_pk = socket.context.tag_picker_scope_pk or None
                            scope_m2m_field = socket.context.tag_picker_scope_m2m_field or None
                            if socket.context.tag_picker_scope_model_label:
                                from django.apps import apps
                                scope_model = apps.get_model(socket.context.tag_picker_scope_model_label)

                            tag = await store.create_tag(
                                field_name,
                                {title_field_name: socket.context.tag_picker_filter},
                                socket.context.tag_picker_item_id,
                                scope_model, scope_pk, scope_m2m_field,
                            )
                            if tag:
                                # Refresh picker
                                available = await store.get_available_tags(
                                    socket.context.tag_picker_item_id,
                                    field_name,
                                    scope_model, scope_pk, scope_m2m_field,
                                    "",
                                )
                                socket.context.tag_picker_items = available
                                socket.context.tag_picker_filter = ""
                                socket.context.tag_picker_can_create = False
                                await self._refresh_view_async(socket)
                                await self._broadcast_change(socket)
                    else:
                        # Complex model - show inline create form
                        tag_create_fields_list = []
                        for f in model_info["fields"]:
                            field_data = {**f, "value": ""}
                            # Pre-fill title field with search text
                            if f["name"] == model_info["title_field"]:
                                field_data["value"] = socket.context.tag_picker_filter
                            tag_create_fields_list.append(field_data)
                        socket.context.tag_create_open = True
                        socket.context.tag_create_fields = tag_create_fields_list
                        socket.context.tag_create_values = {
                            f["name"]: f["value"] for f in tag_create_fields_list if f["value"]
                        }
                        socket.context.tag_create_error = ""
                return

            if event == "update_tag_create_field":
                field_name = payload.get("field", "")
                value = payload.get("value", "") or payload.get(field_name, "")
                socket.context.tag_create_values[field_name] = value
                for f in socket.context.tag_create_fields:
                    if f["name"] == field_name:
                        f["value"] = value
                        break
                return

            if event == "cancel_tag_create":
                socket.context.tag_create_open = False
                socket.context.tag_create_fields = []
                socket.context.tag_create_values = {}
                socket.context.tag_create_error = ""
                return

            if event == "save_tag_create":
                tag_field = socket.context.tag_picker_field
                tc_info = next((t for t in tag_configs_resolved if t["conf"].field_name == tag_field), None)
                if tc_info and tc_info["model_info"]:
                    model_info = tc_info["model_info"]
                    # Validate required fields
                    missing = []
                    for f in model_info["fields"]:
                        if f["required"] and not socket.context.tag_create_values.get(f["name"]):
                            missing.append(f["label"])
                    if missing:
                        socket.context.tag_create_error = f"Required: {', '.join(missing)}"
                        return

                    scope_model = None
                    scope_pk = socket.context.tag_picker_scope_pk or None
                    scope_m2m_field = socket.context.tag_picker_scope_m2m_field or None
                    if socket.context.tag_picker_scope_model_label:
                        from django.apps import apps
                        scope_model = apps.get_model(socket.context.tag_picker_scope_model_label)

                    tag = await store.create_tag(
                        tag_field,
                        socket.context.tag_create_values,
                        socket.context.tag_picker_item_id,
                        scope_model, scope_pk, scope_m2m_field,
                    )
                    if tag:
                        # Refresh picker
                        available = await store.get_available_tags(
                            socket.context.tag_picker_item_id,
                            tag_field,
                            scope_model, scope_pk, scope_m2m_field, "",
                        )
                        socket.context.tag_picker_items = available
                        socket.context.tag_picker_filter = ""
                        socket.context.tag_picker_can_create = False
                        socket.context.tag_create_open = False
                        socket.context.tag_create_fields = []
                        socket.context.tag_create_values = {}
                        socket.context.tag_create_error = ""
                        await self._refresh_view_async(socket)
                        await self._broadcast_change(socket)
                    else:
                        socket.context.tag_create_error = "Failed to create tag"
                return

            # Inline create events
            if event == "open_inline_create":
                item_id = payload.get("item_id", "")
                relation = payload.get("relation", "")
                info = inline_info_by_name.get(relation)
                if item_id and info:
                    target_model = info["target_model"]
                    # Build target model's creatable fields
                    target_create_fields = []
                    if hasattr(target_model, 'get_creatable_fields'):
                        raw_fields = target_model.get_creatable_fields()
                    else:
                        raw_fields = []
                    for i, f in enumerate(raw_fields):
                        field_data = {**f, "value": "", "autofocus": i == 0}
                        if f.get("field_type") == "fk":
                            choices = await store.get_fk_choices_for_model(
                                target_model._meta.label, f["name"]
                            )
                            field_data["choices"] = choices
                            field_data["field_type"] = "select"
                        target_create_fields.append(field_data)

                    # Build through model's extra fields
                    through_extra = model.get_inline_extra_fields(info)
                    through_model = info["through_model"]

                    # Resolve scoped tag choices for the through model
                    scoped_tag_choices = await _resolve_inline_tag_choices(
                        through_model, info["link_fk"], item_id
                    )

                    through_create_fields = []
                    for f in through_extra:
                        field_data = {**f, "value": f.get("default", ""), "autofocus": False}
                        if f.get("field_type") == "fk" and f["name"] in scoped_tag_choices:
                            field_data["choices"] = scoped_tag_choices[f["name"]]
                            field_data["field_type"] = "select"
                        elif f.get("field_type") == "fk":
                            choices = await store.get_fk_choices_for_model(
                                through_model._meta.label, f["name"]
                            )
                            field_data["choices"] = choices
                            field_data["field_type"] = "select"
                        through_create_fields.append(field_data)

                    socket.context.inline_create_open = True
                    socket.context.inline_create_relation = relation
                    socket.context.inline_create_item_id = item_id
                    socket.context.inline_create_target_fields = target_create_fields
                    socket.context.inline_create_through_fields = through_create_fields
                    socket.context.inline_create_target_values = {}
                    socket.context.inline_create_through_values = {}
                    socket.context.inline_create_error = ""
                return

            if event == "close_inline_create":
                socket.context.inline_create_open = False
                socket.context.inline_create_relation = ""
                socket.context.inline_create_item_id = ""
                socket.context.inline_create_target_fields = []
                socket.context.inline_create_through_fields = []
                socket.context.inline_create_target_values = {}
                socket.context.inline_create_through_values = {}
                socket.context.inline_create_error = ""
                return

            if event == "update_inline_create_field":
                # Update target fields
                for f in socket.context.inline_create_target_fields:
                    name = f["name"]
                    if name in payload:
                        value = payload[name]
                        if isinstance(value, list) and len(value) == 1:
                            value = value[0]
                        f["value"] = value
                        socket.context.inline_create_target_values[name] = value
                # Update through fields
                for f in socket.context.inline_create_through_fields:
                    name = f["name"]
                    if name in payload:
                        value = payload[name]
                        if isinstance(value, list) and len(value) == 1:
                            value = value[0]
                        f["value"] = value
                        socket.context.inline_create_through_values[name] = value
                return

            if event == "save_inline_create":
                relation = socket.context.inline_create_relation
                info = inline_info_by_name.get(relation)
                if not info:
                    return

                # Validate required fields
                missing = []
                target_model = info["target_model"]
                if hasattr(target_model, 'get_creatable_fields'):
                    for f in target_model.get_creatable_fields():
                        if f["required"] and not socket.context.inline_create_target_values.get(f["name"]):
                            missing.append(f["label"])
                for f in socket.context.inline_create_through_fields:
                    if f.get("required") and not socket.context.inline_create_through_values.get(f["name"]):
                        missing.append(f["label"])

                if missing:
                    socket.context.inline_create_error = f"Required: {', '.join(missing)}"
                    return

                result = await store.create_inline_item(
                    info,
                    socket.context.inline_create_item_id,
                    socket.context.inline_create_target_values,
                    socket.context.inline_create_through_values,
                )
                if not result:
                    socket.context.inline_create_error = "Failed to create item"
                    return

                # Reset state
                socket.context.inline_create_open = False
                socket.context.inline_create_relation = ""
                socket.context.inline_create_item_id = ""
                socket.context.inline_create_target_fields = []
                socket.context.inline_create_through_fields = []
                socket.context.inline_create_target_values = {}
                socket.context.inline_create_through_values = {}
                socket.context.inline_create_error = ""

                await self._refresh_view_async(socket)
                await self._broadcast_change(socket)
                return

            if event == "remove_inline_item":
                through_pk = payload.get("through_pk", "")
                # Find which inline relation this belongs to
                for info in inline_infos:
                    success = await store.delete_through_item(info, through_pk)
                    if success:
                        await self._refresh_view_async(socket)
                        await self._broadcast_change(socket)
                        break
                return

            if event == "adjust_inline_field":
                through_pk = payload.get("through_pk", "")
                field_name = payload.get("field", "")
                delta = int(payload.get("delta", 0))
                for info in inline_infos:
                    obj = await store.get_through_item(info, through_pk)
                    if obj is not None:
                        current = getattr(obj, field_name, 4)
                        new_val = max(1, min(10, current + delta))
                        await store.update_through_field(info, through_pk, field_name, new_val)
                        await self._refresh_view_async(socket)
                        await self._broadcast_change(socket)
                        break
                return

            if event == "start_inline_target_edit":
                target_pk = payload.get("target_pk", "")
                field_name = payload.get("field", "")
                if target_pk and field_name:
                    edit_key = f"target:{target_pk}:{field_name}"
                    session_id = socket.context.session_id
                    for info in inline_infos:
                        val = await store.get_inline_target_field_value(info, target_pk, field_name)
                        if val is not None:
                            target_label = info["target_model"]._meta.label_lower
                            if acquire_lock(target_label, target_pk, field_name, session_id):
                                socket.context.editing[edit_key] = str(val) if val else ""
                                await self._refresh_view_async(socket)
                                await self._broadcast_change(socket)
                                target_store = get_store(info["target_model"])
                                await socket.broadcast(target_store.channel, {"action": "state_changed"})
                            break
                return

            if event == "update_inline_target_draft":
                target_pk = payload.get("target_pk", "")
                field_name = payload.get("field", "")
                value = payload.get("value", "")
                if isinstance(value, list):
                    value = value[0] if value else ""
                if target_pk and field_name:
                    edit_key = f"target:{target_pk}:{field_name}"
                    socket.context.editing[edit_key] = value
                    self._refresh_view(socket)
                return

            if event == "save_inline_target_edit":
                target_pk = payload.get("target_pk", "")
                field_name = payload.get("field", "")
                session_id = socket.context.session_id
                if target_pk and field_name:
                    edit_key = f"target:{target_pk}:{field_name}"
                    value = socket.context.editing.get(edit_key, "")
                    for info in inline_infos:
                        success = await store.set_inline_target_field_value(info, target_pk, field_name, value)
                        if success:
                            target_label = info["target_model"]._meta.label_lower
                            release_lock(target_label, target_pk, field_name, session_id)
                            target_store = get_store(info["target_model"])
                            await socket.broadcast(target_store.channel, {"action": "state_changed"})
                            break
                    if edit_key in socket.context.editing:
                        del socket.context.editing[edit_key]
                    await self._refresh_view_async(socket)
                    await self._broadcast_change(socket)
                return

            if event == "cancel_inline_target_edit":
                target_pk = payload.get("target_pk", "")
                field_name = payload.get("field", "")
                session_id = socket.context.session_id
                if target_pk and field_name:
                    edit_key = f"target:{target_pk}:{field_name}"
                    for info in inline_infos:
                        target_label = info["target_model"]._meta.label_lower
                        if release_lock(target_label, target_pk, field_name, session_id):
                            target_store = get_store(info["target_model"])
                            await socket.broadcast(target_store.channel, {"action": "state_changed"})
                            break
                    if edit_key in socket.context.editing:
                        del socket.context.editing[edit_key]
                    await self._refresh_view_async(socket)
                    await self._broadcast_change(socket)
                return

            if event == "change_inline_through_field":
                through_pk = payload.get("through_pk", "")
                field_name = payload.get("field", "")
                value = payload.get("value", "")
                if isinstance(value, list):
                    value = value[0] if value else ""
                if through_pk and field_name:
                    # Convert empty string to None for nullable FK fields
                    field_value = int(value) if value else None
                    for info in inline_infos:
                        success = await store.update_through_field(
                            info, through_pk, f"{field_name}_id", field_value
                        )
                        if success:
                            await self._refresh_view_async(socket)
                            await self._broadcast_change(socket)
                            break
                return

            # Try field events first
            if await self.handle_field_event(event, payload, socket):
                return

            # Try item events
            if await self.handle_item_event(event, payload, socket):
                return

        async def handle_info(self, event: InfoEvent, socket: LiveViewSocket[ModelContext]):
            """Handle pub/sub messages from other clients or Django signals."""
            subscribed_channels = {store.channel}
            for info in inline_infos:
                subscribed_channels.add(get_store(info["target_model"]).channel)
            if event.name not in subscribed_channels:
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
            if socket.context.view_mode == "grid":
                socket.context.items = await self._build_grid_data(
                    player_id=socket.context.player_id,
                )
            else:
                socket.context.items = await self._build_items_data(
                    socket.context.session_id, socket.context.editing, socket.context.filters,
                    player_id=socket.context.player_id,
                )
                # Update detail breadcrumb with current item name
                if socket.context.detail_item_id and socket.context.breadcrumbs:
                    item_name = await self._get_item_name(socket.context.detail_item_id)
                    if item_name:
                        socket.context.breadcrumbs[-1] = {"label": item_name, "url": None}

        async def _broadcast_change(self, socket: LiveViewSocket[ModelContext]):
            """Broadcast state change to other clients."""
            await socket.broadcast(store.channel, {"action": "state_changed"})

        async def _build_grid_data(self, player_id: int | None = None) -> list[dict]:
            """Build simplified item data for the grid view."""
            # Check model-level visibility
            if conf.visible_to is not None:
                from asgiref.sync import sync_to_async as _sta
                is_visible = await _sta(conf.visible_to, thread_sensitive=False)(player_id)
                if not is_visible:
                    return []

            qs_hook = None
            if conf.filter_queryset is not None:
                qs_hook = lambda qs: conf.filter_queryset(qs, player_id)

            items = await store.get_items(qs_hook=qs_hook)
            result = []
            list_field_names = list(conf.list_fields) if conf.list_fields else []
            for item in items:
                title_val = str(getattr(item, title_field, item)) if title_field else str(item)
                # Build display fields (excluding the title field to avoid duplication)
                display_fields = []
                for fname in list_field_names:
                    if fname == title_field:
                        continue
                    val = getattr(item, fname, "")
                    if hasattr(val, 'pk'):
                        str_val = str(val)
                    else:
                        str_val = str(val) if val else ""
                    if str_val:
                        display_fields.append({"value": str_val})
                result.append({
                    "id": str(item.pk),
                    "title": title_val,
                    "display_fields": display_fields,
                })
            return result

        async def _build_items_data(self, session_id: str, editing: dict[str, str], filters: dict | None = None, player_id: int | None = None) -> list[dict]:
            """Build the items data for the template."""
            # Check model-level visibility
            if conf.visible_to is not None:
                from asgiref.sync import sync_to_async as _sta
                is_visible = await _sta(conf.visible_to, thread_sensitive=False)(player_id)
                if not is_visible:
                    return []

            # Apply queryset filter hook if configured
            qs_hook = None
            if conf.filter_queryset is not None:
                qs_hook = lambda qs: conf.filter_queryset(qs, player_id)

            items = await store.get_items(filters, qs_hook=qs_hook)
            result = []
            for item in items:
                # Pre-fetch tag data for this item
                tag_data = None
                if has_tag_fields:
                    tag_data = []
                    for tc_info in tag_configs_resolved:
                        tc = tc_info["conf"]
                        tags = await store.get_tags_for_item(str(item.pk), tc.field_name)
                        multiple = tc_info["model_info"]["multiple"] if tc_info["model_info"] else True
                        sortable = store.is_tag_field_sortable(tc.field_name)
                        tag_data.append({
                            "field_name": tc.field_name,
                            "label": tc_info["label"],
                            "tags": tags,
                            "multiple": multiple,
                            "sortable": sortable,
                        })

                # Pre-fetch inline items
                inline_sections = None
                if has_inline:
                    inline_sections = []
                    for info in inline_infos:
                        items_data = await store.get_inline_items(str(item.pk), info)
                        # Enrich with editing state and markdown rendering
                        target_model = info["target_model"]
                        target_conf = target_model.get_alive_conf() if hasattr(target_model, 'get_alive_conf') else None
                        target_editable = set(target_conf.get_editable_fields()) if target_conf else set()
                        target_label = target_model._meta.label_lower
                        for item_d in items_data:
                            tpk = item_d.get("target_pk", "")
                            # Editable target fields
                            for fname, val in item_d.get("target_fields", {}).items():
                                edit_key = f"target:{tpk}:{fname}"
                                is_editing = edit_key in editing
                                lock_holder = get_lock_holder(target_label, tpk, fname)
                                is_locked = lock_holder is not None and lock_holder != session_id
                                item_d[f"target_{fname}_editing"] = is_editing
                                item_d[f"target_{fname}_editing_value"] = editing.get(edit_key, "")
                                item_d[f"target_{fname}_locked"] = is_locked
                                item_d[f"target_{fname}_editable"] = fname in target_editable
                                item_d[f"target_{fname}_html"] = render_markdown_safe(val) if val else ""
                        # Enrich with scoped tag choices for through model tag fields
                        through_model = info["through_model"]
                        tag_choices = await _resolve_inline_tag_choices(
                            through_model, info["link_fk"], str(item.pk)
                        )
                        if tag_choices:
                            for item_d in items_data:
                                tag_fields_list = []
                                for fname, choices in tag_choices.items():
                                    tag_fields_list.append({
                                        "field_name": fname,
                                        "current_pk": item_d.get("through_fields", {}).get(f"{fname}_pk", ""),
                                        "tag_choices": choices,
                                    })
                                item_d["inline_tag_fields"] = tag_fields_list
                        # Enrich with display data if the through model provides it
                        if hasattr(through_model, 'get_inline_display_data'):
                            for item_d in items_data:
                                item_d.update(through_model.get_inline_display_data(item_d))
                        # Group items if the through model supports it
                        if hasattr(through_model, 'get_inline_groups'):
                            from asgiref.sync import sync_to_async as _sta
                            groups = await _sta(
                                through_model.get_inline_groups, thread_sensitive=False
                            )(items_data, parent_item=item)
                        else:
                            groups = [{"label": "", "related_items": items_data}]
                        inline_sections.append({
                            "relation_name": info["relation_name"],
                            "label": info["label"],
                            "groups": groups,
                        })

                item_data = render_item_data(
                    item, fields, session_id, editing, store,
                    title_field, content_fields, fk_field_names, tag_data,
                    inline_sections, compact_field_names,
                )
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
            return LiveRender(template_file(INDEX_TEMPLATE_PATH), context, meta)

        async def mount(self, socket: LiveViewSocket[IndexContext], session: dict[str, Any]):
            player_id = session.get("player_id")

            # Filter models by visibility
            from asgiref.sync import sync_to_async as _sta
            visible = []
            for info in models_info:
                model_cls = info.get("_model")
                if model_cls:
                    model_conf = model_cls.get_alive_conf()
                    if model_conf.visible_to is not None:
                        is_visible = await _sta(model_conf.visible_to, thread_sensitive=False)(player_id)
                        if not is_visible:
                            continue
                visible.append(info)

            socket.context = IndexContext(items=visible)

    return IndexLiveView
