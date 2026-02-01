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
    field_names: list[str] = field(default_factory=list)
    title_field: str = ""
    content_fields: list[str] = field(default_factory=list)


def create_model_liveview(model: Type[models.Model]) -> Type[LiveView]:
    """
    Factory function to create a LiveView class for a Django model.

    Args:
        model: The Django model class (must have AliveMixin)

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
            items_data = await self._build_items_data(session_id, editing)

            # Content fields are all fields except the title field
            content_field_list = [f for f in fields if f != title_field]

            socket.context = ModelContext(
                items=items_data,
                session_id=session_id,
                editing=editing,
                model_name=model_name,
                field_names=list(fields),
                title_field=title_field or "",
                content_fields=content_field_list,
            )

            if is_connected(socket):
                await socket.subscribe(store.channel)

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
                socket.context.session_id, socket.context.editing
            )

        async def _broadcast_change(self, socket: LiveViewSocket[ModelContext]):
            """Broadcast state change to other clients."""
            await socket.broadcast(store.channel, {"action": "state_changed"})

        async def _build_items_data(self, session_id: str, editing: dict[str, str]) -> list[dict]:
            """Build the items data for the template."""
            items = await store.get_items()
            return [
                render_item_data(item, fields, session_id, editing, store, title_field, content_fields)
                for item in items
            ]

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
