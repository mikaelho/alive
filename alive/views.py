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
from .store import get_store, DjangoDataStore, acquire_lock, release_lock, release_all_locks, get_lock_holder
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
    frame: dict = field(default_factory=dict)
    # Quick dice rolls (sidebar)
    quick_d6: int = 6
    quick_d6_svg: str = ""
    quick_d12: int = 12


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
    create_title: str = ""
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
    # Frame data (populated by app's frame_context_provider)
    frame: dict = field(default_factory=dict)
    # Hand footer state (for player-role users)
    hand_is_player: bool = False
    hand_character_id: int | None = None
    hand_card_count: int = 0
    hand_drawn: bool = False
    hand_cards: list[dict] = field(default_factory=list)
    hand_draw_options: list[int] = field(default_factory=list)
    hand_active_situation_id: int | None = None
    # Situation page state
    situation_cards: list[dict] = field(default_factory=list)
    past_situations: list[dict] = field(default_factory=list)
    active_situation_name: str = ""
    active_situation_notes: str = ""
    situation_dice: list[int] = field(default_factory=list)
    situation_assignments: dict = field(default_factory=dict)
    situation_dice_assigned: bool = False
    situation_resolved: bool = False
    situation_all_assigned: bool = False
    # Situation card editing (keeper)
    situation_card_editing_id: str = ""
    situation_card_editing_field: str = ""
    situation_card_editing_value: str = ""
    # Keeper state
    is_keeper: bool = False
    keeper_character_id: int | None = None
    keeper_available_cards: list[dict] = field(default_factory=list)
    keeper_adding: bool = False
    keeper_creating: bool = False
    # Map state
    hex_map_svg: str = ""
    hex_map_edit: bool = False
    hex_map_palette: str = ""
    hex_overlay_palette: str = ""
    hex_active_symbol: str = ""
    hex_active_overlay: str = ""
    hex_overlay_mode: bool = False
    hex_show_overlays: bool = False
    hex_map_id: int | None = None
    hex_river_drawing: bool = False
    hex_current_river: list[str] = field(default_factory=list)
    hex_notes_mode: bool = False
    hex_selected_hex: str = ""
    hex_selected_note: str = ""
    hex_note_html: str = ""
    hex_note_editing: bool = False
    # Timeline / party location state (map page)
    timeline_entries: list[dict] = field(default_factory=list)
    party_location: str = ""
    # Map page create dialog
    map_create_open: bool = False
    map_create_type: str = ""
    map_create_name: str = ""
    map_create_notes: str = ""
    map_create_error: str = ""
    # Quick dice rolls (sidebar)
    quick_d6: int = 6
    quick_d6_svg: str = ""
    quick_d12: int = 12
    # Map page detail popup
    map_detail: dict = field(default_factory=dict)
    map_detail_editing: str = ""
    map_detail_draft: str = ""
    # Map situation overlay (full situation mode on map page)
    map_situation_active: bool = False


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
            if conf.template:
                custom_path = str(TEMPLATE_DIR / conf.template)
                return LiveRender(template_file(custom_path), context, meta)
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

            # Hand footer: detect player role
            player_role = session.get("player_role")
            character_id = session.get("character_id")
            hand_is_player = player_role == "player" and character_id is not None

            # Frame context from app
            from alive import _frame_context_provider
            frame_data = {}
            if _frame_context_provider:
                frame_data = await _frame_context_provider(session)

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
                frame=frame_data,
                hand_is_player=hand_is_player,
                hand_character_id=character_id if hand_is_player else None,
                is_keeper=player_role == "keeper",
                keeper_character_id=character_id if player_role == "keeper" else None,
            )

            # Set initial d6 SVG with pips
            from alive.ui import render_die_svg
            socket.context.quick_d6_svg = render_die_svg(socket.context.quick_d6, css_class="h-8 w-8")

            if hand_is_player:
                await self._load_hand_data(socket)

            if is_connected(socket):
                await socket.subscribe(store.channel)
                # Subscribe to inline target model channels for cross-view lock updates
                for info in inline_infos:
                    target_store = get_store(info["target_model"])
                    if target_store.channel != store.channel:
                        await socket.subscribe(target_store.channel)
                # Subscribe to Card channel for hand footer lock updates
                if hand_is_player:
                    from django.apps import apps as _apps
                    _Card = _apps.get_model('cards', 'Card')
                    _card_store = get_store(_Card)
                    if _card_store.channel not in {store.channel} | {get_store(i["target_model"]).channel for i in inline_infos}:
                        await socket.subscribe(_card_store.channel)

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

            # Load custom template data if applicable
            await self._load_situation_data(socket)
            await self._load_map_data(socket)

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
                socket.context.create_title = model_display_name_singular
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
                if socket.context.keeper_creating:
                    socket.context.keeper_creating = False
                    socket.context.keeper_adding = False
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
                if socket.context.keeper_creating:
                    # Keeper card creation: validate against Card fields, create Card + CharacterCard + add to situation
                    missing = []
                    for f in socket.context.create_fields:
                        if f["required"] and not socket.context.create_values.get(f["name"]):
                            missing.append(f["label"])
                    if missing:
                        socket.context.create_error = f"Required: {', '.join(missing)}"
                        return

                    from django.apps import apps as _apps_ksc
                    Card = _apps_ksc.get_model('cards', 'Card')
                    card_store = get_store(Card)
                    card = await card_store.create_item(socket.context.create_values)
                    if not card:
                        socket.context.create_error = "Failed to create card"
                        return

                    situation_id = socket.context.hand_active_situation_id
                    keeper_char_id = socket.context.keeper_character_id
                    if situation_id and keeper_char_id:
                        from asgiref.sync import sync_to_async as _sta_ksc

                        @_sta_ksc(thread_sensitive=False)
                        def _link_card():
                            CharacterCard = _apps_ksc.get_model('cards', 'CharacterCard')
                            Situation = _apps_ksc.get_model('cards', 'Situation')
                            sit = Situation.objects.get(pk=situation_id)
                            if sit.dice:
                                return
                            cc = CharacterCard.objects.create(
                                character_id=keeper_char_id,
                                card=card,
                                level=4,
                            )
                            sit.cards.add(cc)

                        await _link_card()

                    socket.context.creating = False
                    socket.context.keeper_creating = False
                    socket.context.keeper_adding = False
                    socket.context.create_values = {}
                    socket.context.create_error = ""
                    await self._refresh_view_async(socket)
                    await self._broadcast_change(socket)
                    return

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

                # Auto-set location for new situations from HexMap party_location
                if conf.template == "situation.html" and item:
                    from asgiref.sync import sync_to_async as _sta_loc
                    from django.apps import apps as _apps_loc

                    _game_id = socket.context.frame.get("game_id")
                    if _game_id:
                        @_sta_loc(thread_sensitive=False)
                        def _set_location():
                            HexMap = _apps_loc.get_model('cards', 'HexMap')
                            hm = HexMap.objects.filter(game_id=_game_id).first()
                            if hm and hm.party_location:
                                item.location = hm.party_location
                                item.save(update_fields=["location"])

                        await _set_location()

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

            if event == "draw_hand":
                count = int(payload.get("count", 1))
                character_id = socket.context.hand_character_id
                if character_id and count > 0:
                    import random
                    from asgiref.sync import sync_to_async as _sta
                    from django.apps import apps

                    @_sta(thread_sensitive=False)
                    def _draw(count=count):
                        CharacterCard = apps.get_model('cards', 'CharacterCard')
                        Hand = apps.get_model('cards', 'Hand')

                        all_cards = list(CharacterCard.objects.filter(character_id=character_id))
                        drawn = random.sample(all_cards, min(count, len(all_cards)))

                        # Delete existing hands for this character
                        Hand.objects.filter(character_id=character_id).delete()

                        # Create new hand
                        hand = Hand.objects.create(name="Hand", character_id=character_id)
                        hand.cards.set(drawn)

                    await _draw()
                    await self._load_hand_data(socket)
                return

            if event == "toggle_hand_situation":
                card_id = payload.get("card_id", "")
                situation_id = socket.context.hand_active_situation_id
                if card_id and situation_id and socket.context.hand_is_player and not socket.context.situation_dice:
                    from asgiref.sync import sync_to_async as _sta
                    from django.apps import apps

                    @_sta(thread_sensitive=False)
                    def _toggle():
                        Situation = apps.get_model('cards', 'Situation')
                        sit = Situation.objects.get(pk=situation_id)
                        if sit.dice:
                            return  # Frozen after roll
                        cc_pk = int(card_id)
                        if sit.cards.filter(pk=cc_pk).exists():
                            sit.cards.remove(cc_pk)
                        else:
                            sit.cards.add(cc_pk)

                    await _toggle()
                    await self._load_hand_data(socket)
                    await self._broadcast_change(socket)
                return

            if event == "remove_situation_card":
                card_id = payload.get("card_id", "")
                situation_id = payload.get("situation_id", "")
                if card_id and situation_id and not socket.context.situation_dice:
                    from asgiref.sync import sync_to_async as _sta
                    from django.apps import apps

                    @_sta(thread_sensitive=False)
                    def _remove():
                        Situation = apps.get_model('cards', 'Situation')
                        sit = Situation.objects.get(pk=int(situation_id))
                        if sit.dice:
                            return  # Frozen after roll
                        sit.cards.remove(int(card_id))

                    await _remove()
                    await self._refresh_view_async(socket)
                    if socket.context.hand_is_player:
                        await self._load_hand_data(socket)
                    await self._broadcast_change(socket)
                return

            if event == "adjust_situation_card_level":
                card_id = payload.get("card_id", "")
                delta = int(payload.get("delta", 0))
                if card_id and delta and socket.context.is_keeper:
                    from asgiref.sync import sync_to_async as _sta
                    from django.apps import apps
                    has_dice = bool(socket.context.situation_dice)

                    @_sta(thread_sensitive=False)
                    def _adjust():
                        if has_dice:
                            SituationCard = apps.get_model('cards', 'SituationCard')
                            sc = SituationCard.objects.get(pk=int(card_id))
                            sc.level = max(1, min(10, sc.level + delta))
                            sc.save(update_fields=["level"])
                        else:
                            CharacterCard = apps.get_model('cards', 'CharacterCard')
                            cc = CharacterCard.objects.get(pk=int(card_id))
                            cc.level = max(1, min(10, cc.level + delta))
                            cc.save(update_fields=["level"])

                    await _adjust()
                    await self._refresh_view_async(socket)
                    await self._broadcast_change(socket)
                return

            if event == "start_situation_card_edit":
                card_id = payload.get("card_id", "")
                field = payload.get("field", "")
                if card_id and field in ("name", "notes") and socket.context.is_keeper:
                    socket.context.situation_card_editing_id = card_id
                    socket.context.situation_card_editing_field = field
                return

            if event == "cancel_situation_card_edit":
                socket.context.situation_card_editing_id = ""
                socket.context.situation_card_editing_field = ""
                socket.context.situation_card_editing_value = ""
                return

            if event == "save_situation_card_edit":
                card_id = payload.get("card_id", "")
                field = payload.get("field", "")
                value = payload.get("value", "")
                if isinstance(value, list):
                    value = value[0] if value else ""
                if card_id and field in ("name", "notes") and socket.context.is_keeper:
                    from asgiref.sync import sync_to_async as _sta
                    from django.apps import apps
                    has_dice = bool(socket.context.situation_dice)
                    value = value.strip()

                    @_sta(thread_sensitive=False)
                    def _save():
                        if has_dice:
                            SituationCard = apps.get_model('cards', 'SituationCard')
                            sc = SituationCard.objects.get(pk=int(card_id))
                            setattr(sc, field, value)
                            sc.save(update_fields=[field])
                        else:
                            CharacterCard = apps.get_model('cards', 'CharacterCard')
                            cc = CharacterCard.objects.select_related('card').get(pk=int(card_id))
                            setattr(cc.card, field, value)
                            cc.card.save(update_fields=[field])

                    await _save()
                    socket.context.situation_card_editing_id = ""
                    socket.context.situation_card_editing_field = ""
                    socket.context.situation_card_editing_value = ""
                    await self._refresh_view_async(socket)
                    await self._broadcast_change(socket)
                else:
                    socket.context.situation_card_editing_id = ""
                    socket.context.situation_card_editing_field = ""
                    socket.context.situation_card_editing_value = ""
                return

            if event == "rename_situation":
                new_name = payload.get("value", "").strip()
                situation_id = socket.context.hand_active_situation_id
                if new_name and situation_id:
                    from asgiref.sync import sync_to_async as _sta
                    from django.apps import apps

                    @_sta(thread_sensitive=False)
                    def _rename():
                        Situation = apps.get_model('cards', 'Situation')
                        Situation.objects.filter(pk=situation_id).update(name=new_name)

                    await _rename()
                    await self._refresh_view_async(socket)
                    await self._broadcast_change(socket)
                return

            if event == "keeper_start_add":
                socket.context.keeper_adding = True
                socket.context.keeper_creating = False
                return

            if event == "keeper_cancel_add":
                socket.context.keeper_adding = False
                if socket.context.keeper_creating:
                    socket.context.keeper_creating = False
                    socket.context.creating = False
                    socket.context.create_values = {}
                    socket.context.create_error = ""
                return

            if event == "keeper_start_create":
                from django.apps import apps as _apps_kc
                Card = _apps_kc.get_model('cards', 'Card')
                card_create_fields = Card.get_creatable_fields()
                fields_with_choices = []
                for i, f in enumerate(card_create_fields):
                    fields_with_choices.append({**f, "value": "", "autofocus": i == 0})
                socket.context.create_fields = fields_with_choices
                socket.context.create_values = {}
                socket.context.create_error = ""
                socket.context.create_title = Card._meta.verbose_name.title()
                socket.context.creating = True
                socket.context.keeper_creating = True
                return

            if event == "keeper_add_card":
                card_id = payload.get("card_id", "")
                situation_id = socket.context.hand_active_situation_id
                if card_id and situation_id and socket.context.is_keeper:
                    from asgiref.sync import sync_to_async as _sta
                    from django.apps import apps

                    @_sta(thread_sensitive=False)
                    def _add():
                        Situation = apps.get_model('cards', 'Situation')
                        sit = Situation.objects.get(pk=situation_id)
                        if sit.dice:
                            return
                        sit.cards.add(int(card_id))

                    await _add()
                    socket.context.keeper_adding = False
                    await self._refresh_view_async(socket)
                    await self._broadcast_change(socket)
                return

            # --- Map editing events ---

            if event == "toggle_map_edit":
                if socket.context.is_keeper:
                    # Commit any in-progress river before leaving edit mode
                    if socket.context.hex_map_edit and socket.context.hex_current_river:
                        await self._commit_river(socket)
                    socket.context.hex_map_edit = not socket.context.hex_map_edit
                    socket.context.hex_active_symbol = ""
                    socket.context.hex_active_overlay = ""
                    socket.context.hex_overlay_mode = False
                    socket.context.hex_river_drawing = False
                    socket.context.hex_current_river = []
                    await self._load_map_data(socket)
                return

            if event == "select_map_symbol":
                # Commit any in-progress river when switching tools
                if socket.context.hex_current_river:
                    await self._commit_river(socket)
                symbol = payload.get("symbol", "")
                socket.context.hex_active_symbol = symbol
                socket.context.hex_active_overlay = ""
                socket.context.hex_overlay_mode = False
                socket.context.hex_river_drawing = False
                socket.context.hex_notes_mode = False
                socket.context.hex_selected_hex = ""
                socket.context.hex_selected_note = ""
                socket.context.hex_note_html = ""
                socket.context.hex_note_editing = False
                await self._load_map_data(socket)
                return

            if event == "toggle_overlays":
                if socket.context.is_keeper:
                    socket.context.hex_show_overlays = not socket.context.hex_show_overlays
                    await self._load_map_data(socket)
                return

            if event == "select_overlay_symbol":
                if socket.context.hex_current_river:
                    await self._commit_river(socket)
                symbol = payload.get("symbol", "")
                socket.context.hex_active_overlay = symbol
                socket.context.hex_active_symbol = ""
                socket.context.hex_overlay_mode = True
                socket.context.hex_show_overlays = True
                socket.context.hex_river_drawing = False
                socket.context.hex_notes_mode = False
                socket.context.hex_selected_hex = ""
                socket.context.hex_selected_note = ""
                socket.context.hex_note_html = ""
                socket.context.hex_note_editing = False
                await self._load_map_data(socket)
                return

            if event == "toggle_notes_mode":
                if socket.context.hex_current_river:
                    await self._commit_river(socket)
                socket.context.hex_notes_mode = not socket.context.hex_notes_mode
                if socket.context.hex_notes_mode:
                    socket.context.hex_active_symbol = ""
                    socket.context.hex_active_overlay = ""
                    socket.context.hex_overlay_mode = False
                    socket.context.hex_river_drawing = False
                else:
                    socket.context.hex_selected_hex = ""
                    socket.context.hex_selected_note = ""
                    socket.context.hex_note_html = ""
                    socket.context.hex_note_editing = False
                await self._load_map_data(socket)
                return

            if event == "save_hex_note":
                map_id = socket.context.hex_map_id
                hex_key = socket.context.hex_selected_hex
                if not map_id or not hex_key or not socket.context.is_keeper:
                    return
                note_text = payload.get("note", "")
                if isinstance(note_text, list):
                    note_text = note_text[0] if note_text else ""

                from asgiref.sync import sync_to_async as _sta

                @_sta(thread_sensitive=False)
                def _save_note():
                    hex_map = model.objects.get(pk=map_id)
                    notes = hex_map.notes or {}
                    if note_text.strip():
                        notes[hex_key] = note_text
                    else:
                        notes.pop(hex_key, None)
                    hex_map.notes = notes
                    hex_map.save(update_fields=["notes"])

                await _save_note()
                socket.context.hex_selected_note = note_text
                socket.context.hex_note_html = render_markdown_safe(note_text) if note_text.strip() else ""
                socket.context.hex_note_editing = False
                await self._load_map_data(socket)
                return

            if event == "edit_hex_note":
                socket.context.hex_note_editing = True
                await self._load_map_data(socket)
                return

            if event == "close_hex_note":
                if socket.context.hex_selected_hex:
                    socket.context.hex_selected_hex = ""
                    socket.context.hex_selected_note = ""
                    socket.context.hex_note_html = ""
                    socket.context.hex_note_editing = False
                    await self._load_map_data(socket)
                return

            if event == "move_party":
                if not socket.context.is_keeper or socket.context.hex_map_edit:
                    return
                col = payload.get("col", "")
                row = payload.get("row", "")
                if col == "" or row == "":
                    return
                target_key = f"{col},{row}"
                current = socket.context.party_location

                if current:
                    from alive.ui import get_adjacent_hexes
                    cc, cr = map(int, current.split(","))
                    adjacent = get_adjacent_hexes(cc, cr)
                    if target_key not in adjacent:
                        return

                map_id = socket.context.hex_map_id
                if not map_id:
                    return

                from asgiref.sync import sync_to_async as _sta

                @_sta(thread_sensitive=False)
                def _move():
                    hex_map = model.objects.get(pk=map_id)
                    if hex_map.party_location:
                        trail = hex_map.party_trail or []
                        trail.append(hex_map.party_location)
                        hex_map.party_trail = trail
                    hex_map.party_location = target_key
                    hex_map.save(update_fields=["party_location", "party_trail"])

                await _move()
                await self._load_map_data(socket)
                await self._broadcast_change(socket)
                return

            # --- Map create dialog ---

            if event == "open_map_create":
                sit_type = payload.get("type", "note")
                socket.context.map_create_open = True
                socket.context.map_create_type = sit_type
                socket.context.map_create_name = ""
                socket.context.map_create_notes = ""
                socket.context.map_create_error = ""
                return

            if event == "map_cancel_create":
                socket.context.map_create_open = False
                socket.context.map_create_type = ""
                socket.context.map_create_name = ""
                socket.context.map_create_notes = ""
                socket.context.map_create_error = ""
                return

            if event == "map_update_create":
                name = payload.get("name", "")
                if isinstance(name, list):
                    name = name[0] if name else ""
                socket.context.map_create_name = name
                notes = payload.get("notes", "")
                if isinstance(notes, list):
                    notes = notes[0] if notes else ""
                socket.context.map_create_notes = notes
                return

            if event == "map_save_create":
                name = socket.context.map_create_name.strip()
                notes = socket.context.map_create_notes.strip()
                sit_type = socket.context.map_create_type or "note"
                if not name:
                    socket.context.map_create_error = "Name is required"
                    return
                game_id = socket.context.frame.get("game_id")
                if not game_id:
                    return

                from asgiref.sync import sync_to_async as _sta
                from django.apps import apps as _apps_mc

                @_sta(thread_sensitive=False)
                def _create_entry():
                    Situation = _apps_mc.get_model('cards', 'Situation')
                    HexMap = _apps_mc.get_model('cards', 'HexMap')
                    loc = ""
                    hm = HexMap.objects.filter(game_id=game_id).first()
                    if hm and hm.party_location:
                        loc = hm.party_location
                    return Situation.objects.create(
                        name=name, notes=notes, game_id=game_id,
                        situation_type=sit_type, location=loc,
                    )

                new_sit = await _create_entry()
                socket.context.map_create_open = False
                socket.context.map_create_type = ""
                socket.context.map_create_name = ""
                socket.context.map_create_notes = ""
                socket.context.map_create_error = ""
                await self._load_map_data(socket)
                await self._broadcast_change(socket)
                return

            if event == "cancel_map_situation":
                situation_id = socket.context.hand_active_situation_id
                if situation_id and socket.context.is_keeper and not socket.context.situation_dice:
                    from asgiref.sync import sync_to_async as _sta
                    from django.apps import apps as _apps_cs

                    @_sta(thread_sensitive=False)
                    def _cancel():
                        Situation = _apps_cs.get_model('cards', 'Situation')
                        sit = Situation.objects.get(pk=situation_id)
                        if sit.dice:
                            return  # Don't cancel after roll
                        sit.delete()

                    await _cancel()
                    socket.context.hand_active_situation_id = None
                    socket.context.active_situation_name = ""
                    socket.context.active_situation_notes = ""
                    socket.context.situation_cards = []
                    socket.context.situation_dice = []
                    socket.context.situation_assignments = {}
                    socket.context.situation_dice_assigned = False
                    socket.context.situation_resolved = False
                    socket.context.situation_all_assigned = False
                    socket.context.map_situation_active = False
                    await self._load_map_data(socket)
                    if socket.context.hand_is_player:
                        await self._load_hand_data(socket)
                    await self._broadcast_change(socket)
                return

            # --- Map detail popup ---

            if event == "open_map_detail":
                entry_id = payload.get("id", "")
                if not entry_id:
                    return
                # Close previous detail (release locks)
                await self._close_map_detail(socket)
                socket.context.map_detail = {"id": entry_id}
                await self._refresh_map_detail(socket)
                return

            if event == "close_map_detail":
                had_editing = bool(socket.context.map_detail_editing)
                await self._close_map_detail(socket)
                if had_editing:
                    await self._broadcast_change(socket)
                return

            if event == "map_start_edit":
                field_name = payload.get("field", "")
                detail_id = (socket.context.map_detail or {}).get("id", "")
                if not field_name or not detail_id:
                    return
                from .store import acquire_lock as _acq

                sid = socket.context.session_id
                if _acq("cards.situation", detail_id, field_name, sid):
                    from asgiref.sync import sync_to_async as _sta
                    from django.apps import apps as _apps_se

                    @_sta(thread_sensitive=False)
                    def _get_value():
                        Situation = _apps_se.get_model('cards', 'Situation')
                        try:
                            s = Situation.objects.get(pk=detail_id)
                            return getattr(s, field_name, "")
                        except Situation.DoesNotExist:
                            return ""

                    val = await _get_value()
                    socket.context.map_detail_editing = field_name
                    socket.context.map_detail_draft = str(val) if val else ""
                    await self._broadcast_change(socket)
                await self._refresh_map_detail(socket)
                return

            if event == "map_update_draft":
                value = payload.get("value", "")
                if isinstance(value, list):
                    value = value[0] if value else ""
                socket.context.map_detail_draft = value
                return

            if event == "map_cancel_edit":
                detail_id = (socket.context.map_detail or {}).get("id", "")
                field_name = socket.context.map_detail_editing
                if detail_id and field_name:
                    from .store import release_lock as _rel
                    _rel("cards.situation", detail_id, field_name,
                         socket.context.session_id)
                socket.context.map_detail_editing = ""
                socket.context.map_detail_draft = ""
                await self._refresh_map_detail(socket)
                await self._broadcast_change(socket)
                return

            if event == "map_save_edit":
                detail_id = (socket.context.map_detail or {}).get("id", "")
                field_name = socket.context.map_detail_editing
                value = socket.context.map_detail_draft
                if not detail_id or not field_name:
                    return

                from .store import get_lock_holder as _glh, release_lock as _rel
                sid = socket.context.session_id
                if _glh("cards.situation", detail_id, field_name) != sid:
                    socket.context.map_detail_editing = ""
                    socket.context.map_detail_draft = ""
                    await self._refresh_map_detail(socket)
                    return

                from asgiref.sync import sync_to_async as _sta
                from django.apps import apps as _apps_sv

                @_sta(thread_sensitive=False)
                def _save_field():
                    Situation = _apps_sv.get_model('cards', 'Situation')
                    try:
                        s = Situation.objects.get(pk=detail_id)
                        setattr(s, field_name, value)
                        s.save(update_fields=[field_name])
                    except Situation.DoesNotExist:
                        pass

                await _save_field()
                _rel("cards.situation", detail_id, field_name, sid)
                socket.context.map_detail_editing = ""
                socket.context.map_detail_draft = ""
                await self._refresh_map_detail(socket)
                await self._load_map_data(socket)
                await self._broadcast_change(socket)
                return

            if event == "start_river":
                # Commit previous river if any, then enter river drawing mode
                if socket.context.hex_current_river:
                    await self._commit_river(socket)
                socket.context.hex_river_drawing = True
                socket.context.hex_active_symbol = ""
                socket.context.hex_active_overlay = ""
                socket.context.hex_overlay_mode = False
                socket.context.hex_notes_mode = False
                socket.context.hex_selected_hex = ""
                socket.context.hex_selected_note = ""
                socket.context.hex_note_html = ""
                socket.context.hex_note_editing = False
                socket.context.hex_current_river = []
                await self._load_map_data(socket)
                return

            if event == "finish_river":
                if socket.context.hex_current_river:
                    await self._commit_river(socket)
                socket.context.hex_current_river = []
                socket.context.hex_river_drawing = False
                await self._load_map_data(socket)
                return

            if event == "undo_river_point":
                if socket.context.hex_current_river:
                    socket.context.hex_current_river = socket.context.hex_current_river[:-1]
                    await self._load_map_data(socket)
                return

            if event == "delete_last_river":
                map_id = socket.context.hex_map_id
                if map_id and socket.context.is_keeper:
                    from asgiref.sync import sync_to_async as _sta

                    @_sta(thread_sensitive=False)
                    def _delete():
                        hex_map = model.objects.get(pk=map_id)
                        rivers = hex_map.rivers or []
                        if rivers:
                            rivers.pop()
                            hex_map.rivers = rivers
                            hex_map.save(update_fields=["rivers"])

                    await _delete()
                    await self._load_map_data(socket)
                    await self._broadcast_change(socket)
                return

            if event == "set_hex":
                map_id = socket.context.hex_map_id
                if not map_id or not socket.context.is_keeper or not socket.context.hex_map_edit:
                    return
                col = payload.get("col", "")
                row = payload.get("row", "")
                if col == "" or row == "":
                    return
                key = f"{col},{row}"

                # Notes mode: select hex and load its note
                if socket.context.hex_notes_mode:
                    from asgiref.sync import sync_to_async as _sta_n

                    @_sta_n(thread_sensitive=False)
                    def _load_note():
                        hex_map = model.objects.get(pk=map_id)
                        notes = hex_map.notes or {}
                        return notes.get(key, "")

                    note = await _load_note()
                    socket.context.hex_selected_hex = key
                    socket.context.hex_selected_note = note
                    socket.context.hex_note_html = render_markdown_safe(note) if note.strip() else ""
                    socket.context.hex_note_editing = not note.strip()
                    await self._load_map_data(socket)
                    return

                # River drawing mode: add hex to current river
                if socket.context.hex_river_drawing:
                    from alive.ui import _find_shared_edge
                    current = socket.context.hex_current_river
                    if current:
                        # Validate adjacency
                        lc, lr = map(int, current[-1].split(","))
                        edge = _find_shared_edge(lc, lr, int(col), int(row))
                        if edge is None:
                            return  # not adjacent, ignore
                    socket.context.hex_current_river = current + [key]
                    await self._load_map_data(socket)
                    return

                # Overlay painting mode
                if socket.context.hex_overlay_mode:
                    overlay = socket.context.hex_active_overlay
                    from asgiref.sync import sync_to_async as _sta

                    # Barrier tool
                    if overlay and overlay.startswith("barrier_"):
                        barrier_arg = overlay.split("_", 1)[1]

                        @_sta(thread_sensitive=False)
                        def _toggle_barrier():
                            hex_map = model.objects.get(pk=map_id)
                            barriers = hex_map.barriers or {}
                            edges = barriers.get(key, [])
                            if barrier_arg == "eraser":
                                # Remove all barriers from this hex
                                barriers.pop(key, None)
                            else:
                                edge_i = int(barrier_arg)
                                if edge_i in edges:
                                    edges.remove(edge_i)
                                else:
                                    edges.append(edge_i)
                                if edges:
                                    barriers[key] = edges
                                else:
                                    barriers.pop(key, None)
                            hex_map.barriers = barriers
                            hex_map.save(update_fields=["barriers"])

                        await _toggle_barrier()
                        await self._load_map_data(socket)
                        return

                    # Regular overlay symbol
                    @_sta(thread_sensitive=False)
                    def _set_overlay():
                        hex_map = model.objects.get(pk=map_id)
                        overlays = hex_map.overlays or {}
                        if overlay:
                            overlays[key] = overlay
                        else:
                            overlays.pop(key, None)
                        hex_map.overlays = overlays
                        hex_map.save(update_fields=["overlays"])

                    await _set_overlay()
                    await self._load_map_data(socket)
                    return

                # Normal symbol painting mode
                symbol = socket.context.hex_active_symbol

                from asgiref.sync import sync_to_async as _sta2

                @_sta2(thread_sensitive=False)
                def _set_hex():
                    hex_map = model.objects.get(pk=map_id)
                    hexes = hex_map.hexes or {}
                    if symbol:
                        hexes[key] = symbol
                    else:
                        hexes.pop(key, None)
                    hex_map.hexes = hexes
                    hex_map.save(update_fields=["hexes"])

                await _set_hex()
                await self._load_map_data(socket)
                await self._broadcast_change(socket)
                return

            if event == "roll_situation":
                situation_id = socket.context.hand_active_situation_id
                if situation_id:
                    import random
                    from asgiref.sync import sync_to_async as _sta
                    from django.apps import apps

                    @_sta(thread_sensitive=False)
                    def _roll():
                        Situation = apps.get_model('cards', 'Situation')
                        Hand = apps.get_model('cards', 'Hand')
                        SituationCard = apps.get_model('cards', 'SituationCard')
                        sit = Situation.objects.get(pk=situation_id)
                        if sit.dice:
                            return  # Already rolled
                        originals = list(
                            sit.cards.select_related('card', 'character').all()
                        )
                        n = len(originals)
                        if n == 0:
                            return
                        sit.dice = [random.randint(1, 6) for _ in range(n + 1)]
                        sit.save(update_fields=["dice"])
                        # Create archived snapshot cards on the situation
                        for cc in originals:
                            SituationCard.objects.create(
                                situation=sit,
                                name=cc.card.name,
                                notes=cc.card.notes or "",
                                level=cc.level,
                                character_name=cc.character.name if cc.character else "",
                            )
                        # Clear the M2M (snapshots replace it)
                        sit.cards.clear()
                        # Remove originals from their owners' hands
                        for cc in originals:
                            for hand in Hand.objects.filter(cards__pk=cc.pk):
                                hand.cards.remove(cc.pk)

                    await _roll()
                    await self._refresh_view_async(socket)
                    if socket.context.hand_is_player:
                        await self._load_hand_data(socket)
                    await self._broadcast_change(socket)
                return

            if event == "assign_die":
                card_id = payload.get("card_id", "")
                die_index = payload.get("die_index", "")
                situation_id = socket.context.hand_active_situation_id
                if card_id and die_index != "" and situation_id:
                    from asgiref.sync import sync_to_async as _sta
                    from django.apps import apps

                    @_sta(thread_sensitive=False)
                    def _assign():
                        Situation = apps.get_model('cards', 'Situation')
                        sit = Situation.objects.get(pk=situation_id)
                        if not sit.dice or sit.dice_assigned:
                            return
                        assignments = sit.assignments or {}
                        assignments[str(card_id)] = int(die_index)
                        sit.assignments = assignments
                        sit.save(update_fields=["assignments"])

                    await _assign()
                    await self._refresh_view_async(socket)
                    if socket.context.hand_is_player:
                        await self._load_hand_data(socket)
                    await self._broadcast_change(socket)
                return

            if event == "unassign_die":
                card_id = payload.get("card_id", "")
                situation_id = socket.context.hand_active_situation_id
                if card_id and situation_id:
                    from asgiref.sync import sync_to_async as _sta
                    from django.apps import apps

                    @_sta(thread_sensitive=False)
                    def _unassign():
                        Situation = apps.get_model('cards', 'Situation')
                        sit = Situation.objects.get(pk=situation_id)
                        if sit.dice_assigned:
                            return
                        assignments = sit.assignments or {}
                        assignments.pop(str(card_id), None)
                        sit.assignments = assignments
                        sit.save(update_fields=["assignments"])

                    await _unassign()
                    await self._refresh_view_async(socket)
                    if socket.context.hand_is_player:
                        await self._load_hand_data(socket)
                    await self._broadcast_change(socket)
                return

            if event == "lock_dice":
                situation_id = socket.context.hand_active_situation_id
                if situation_id:
                    from asgiref.sync import sync_to_async as _sta
                    from django.apps import apps

                    @_sta(thread_sensitive=False)
                    def _lock():
                        Situation = apps.get_model('cards', 'Situation')
                        sit = Situation.objects.get(pk=situation_id)
                        if not sit.dice or sit.dice_assigned:
                            return
                        card_count = sit.situation_cards.count()
                        if len(sit.assignments or {}) < card_count:
                            return
                        sit.dice_assigned = True
                        sit.save(update_fields=["dice_assigned"])

                    await _lock()
                    await self._refresh_view_async(socket)
                    await self._broadcast_change(socket)
                return

            if event == "toggle_used_card":
                card_id = payload.get("card_id", "")
                situation_id = socket.context.hand_active_situation_id
                if card_id and situation_id and socket.context.situation_dice_assigned:
                    from asgiref.sync import sync_to_async as _sta
                    from django.apps import apps

                    @_sta(thread_sensitive=False)
                    def _toggle_used():
                        SituationCard = apps.get_model('cards', 'SituationCard')
                        sc = SituationCard.objects.get(pk=int(card_id), situation_id=situation_id)
                        sc.used = not sc.used
                        sc.save(update_fields=["used"])

                    await _toggle_used()
                    await self._refresh_view_async(socket)
                    await self._broadcast_change(socket)
                return

            if event == "resolve_situation":
                situation_id = socket.context.hand_active_situation_id
                if not situation_id:
                    return
                from asgiref.sync import sync_to_async as _sta
                from django.apps import apps

                @_sta(thread_sensitive=False)
                def _resolve():
                    Situation = apps.get_model('cards', 'Situation')
                    sit = Situation.objects.filter(pk=situation_id, resolved=False).first()
                    if sit:
                        sit.resolved = True
                        sit.save(update_fields=["resolved"])

                await _resolve()
                await self._refresh_view_async(socket)
                await self._broadcast_change(socket)
                return

            # Quick dice rolls (sidebar)
            if event == "quick_roll_d6":
                import random
                from alive.ui import render_die_svg
                v = random.randint(1, 6)
                socket.context.quick_d6 = v
                socket.context.quick_d6_svg = render_die_svg(v, css_class="h-8 w-8")
                return

            if event == "quick_roll_d12":
                import random
                socket.context.quick_d12 = random.randint(1, 12)
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
            # Include Card channel if hand is active
            if socket.context.hand_is_player:
                from django.apps import apps as _apps
                _Card = _apps.get_model('cards', 'Card')
                subscribed_channels.add(get_store(_Card).channel)
            if event.name not in subscribed_channels:
                return

            data = event.payload
            action = data.get("action", "")

            if action in ("state_changed", "locks_released", "item_created", "item_deleted"):
                await self._refresh_view_async(socket)
                if socket.context.hand_is_player:
                    await self._load_hand_data(socket)
            elif action == "conflict":
                conflict_key = data.get("key", "")
                if conflict_key in socket.context.editing:
                    del socket.context.editing[conflict_key]
                await self._refresh_view_async(socket)
                if socket.context.hand_is_player:
                    await self._load_hand_data(socket)

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
            # Load custom template data if applicable
            await self._load_situation_data(socket)
            await self._load_map_data(socket)

        async def _broadcast_change(self, socket: LiveViewSocket[ModelContext]):
            """Broadcast state change to other clients."""
            await socket.broadcast(store.channel, {"action": "state_changed"})

        async def _load_situation_data(self, socket: LiveViewSocket[ModelContext]):
            """Load situation-specific context when viewing the Situation model."""
            is_situation_page = conf.template == "situation.html"
            is_map_page = conf.template == "map.html"
            if not is_situation_page and not is_map_page:
                return

            game_id = socket.context.frame.get("game_id")
            if not game_id:
                return

            from asgiref.sync import sync_to_async as _sta
            from django.apps import apps

            @_sta(thread_sensitive=False)
            def _fetch():
                Situation = apps.get_model('cards', 'Situation')

                if is_map_page:
                    # Map page: only show unresolved situations (not notes)
                    active = Situation.objects.filter(
                        game_id=game_id, resolved=False, situation_type="situation"
                    ).order_by('-pk').first()
                    past = []
                    if not active:
                        return None, [], [], [], {}, False, False
                else:
                    # Situation page: show most recent regardless of status
                    situations = list(
                        Situation.objects.filter(game_id=game_id).order_by('-pk')
                    )
                    if not situations:
                        return None, [], [], [], {}, False, False
                    active = situations[0]
                    past = [{"id": str(s.pk), "name": s.name} for s in situations[1:]]
                dice = active.dice or []
                assignments = active.assignments or {}

                # Compute which die indices are already assigned
                assigned_indices = set(assignments.values())

                # Load cards in the active situation
                from cards.models.card import get_bands_for_level, get_band_for_die
                cards = []
                if dice:
                    # Post-roll: read from SituationCard snapshots
                    for sc in active.situation_cards.all():
                        card_id = str(sc.pk)
                        assigned_die_index = assignments.get(card_id)
                        assigned_die_value = None
                        assigned_band_label = None
                        if assigned_die_index is not None and assigned_die_index < len(dice):
                            assigned_die_value = dice[assigned_die_index]
                            assigned_band_label = get_band_for_die(sc.level, assigned_die_value)

                        card_bands = get_bands_for_level(sc.level)
                        for band in card_bands:
                            band["highlighted"] = (band["label"] == assigned_band_label) if assigned_band_label else False

                        available_dice = []
                        for idx, val in enumerate(dice):
                            if idx not in assigned_indices:
                                available_dice.append({"index": idx, "value": val})

                        cards.append({
                            "id": card_id,
                            "name": sc.name,
                            "notes": sc.notes,
                            "character_name": sc.character_name,
                            "level": sc.level,
                            "bands": card_bands,
                            "assigned_die_value": assigned_die_value,
                            "assigned_die_index": assigned_die_index,
                            "assigned_band": assigned_band_label or "",
                            "available_dice": available_dice,
                            "used": sc.used,
                        })
                else:
                    # Pre-roll: read from CharacterCard M2M
                    for cc in active.cards.select_related('card', 'character').all():
                        cards.append({
                            "id": str(cc.pk),
                            "name": cc.card.name,
                            "notes": cc.card.notes or "",
                            "character_name": cc.character.name if cc.character else "",
                            "level": cc.level,
                            "bands": get_bands_for_level(cc.level),
                            "assigned_die_value": None,
                            "assigned_die_index": None,
                            "available_dice": [],
                        })

                return active, cards, past, dice, assignments, active.dice_assigned, active.resolved

            active, cards, past, dice, assignments, dice_assigned, resolved = await _fetch()

            if active is None:
                socket.context.hand_active_situation_id = None
                socket.context.active_situation_name = ""
                socket.context.active_situation_notes = ""
                socket.context.situation_cards = []
                socket.context.past_situations = []
                socket.context.situation_dice = []
                socket.context.situation_assignments = {}
                socket.context.situation_dice_assigned = False
                socket.context.situation_resolved = False
                socket.context.situation_all_assigned = False
                if is_map_page:
                    socket.context.map_situation_active = False
                return

            # Build enriched dice list for display with SVGs
            from alive.ui import render_die_svg, DIE_CSS
            assigned_indices = set(assignments.values()) if assignments else set()
            # Reverse mapping: die index -> card_id
            index_to_card = {v: k for k, v in assignments.items()} if assignments else {}
            dice_display = [
                {"index": i, "value": v, "assigned": i in assigned_indices,
                 "card_id": index_to_card.get(i, ""),
                 "svg": render_die_svg(v, css_class="h-8 w-8")}
                for i, v in enumerate(dice)
            ] if dice else []

            # Add SVGs to card data
            dashed_svg = render_die_svg(0, css_class="h-8 w-8", dashed=True)
            for card in cards:
                if card["assigned_die_value"] is not None:
                    card["assigned_die_svg"] = render_die_svg(card["assigned_die_value"], css_class="h-8 w-8")
                card["placeholder_svg"] = dashed_svg
                # Add SVGs to available dice
                for die in card.get("available_dice", []):
                    die["svg"] = render_die_svg(die["value"], css_class="h-8 w-8")

            # Annotate cards with editing state for keeper
            edit_id = socket.context.situation_card_editing_id
            edit_field = socket.context.situation_card_editing_field
            edit_value = socket.context.situation_card_editing_value
            for card in cards:
                card["editing_name"] = (card["id"] == edit_id and edit_field == "name")
                card["editing_notes"] = (card["id"] == edit_id and edit_field == "notes")
                card["editing_value"] = edit_value if card["id"] == edit_id else ""

            socket.context.hand_active_situation_id = active.pk
            socket.context.active_situation_name = active.name
            socket.context.active_situation_notes = active.notes or ""
            socket.context.situation_cards = cards
            socket.context.past_situations = past
            socket.context.situation_dice = dice_display
            socket.context.situation_assignments = assignments
            socket.context.situation_dice_assigned = dice_assigned
            socket.context.situation_resolved = resolved
            socket.context.situation_all_assigned = bool(dice and cards and len(assignments) >= len(cards))

            if is_map_page:
                socket.context.map_situation_active = not resolved

            # Load keeper's available cards for the picker
            if socket.context.is_keeper and socket.context.keeper_character_id and not dice:
                keeper_char_id = socket.context.keeper_character_id

                @_sta(thread_sensitive=False)
                def _fetch_keeper_cards():
                    CharacterCard = apps.get_model('cards', 'CharacterCard')
                    situation_card_pks = set(
                        active.cards.values_list('pk', flat=True)
                    ) if active else set()
                    return [
                        {"id": str(cc.pk), "name": cc.card.name, "level": cc.level}
                        for cc in CharacterCard.objects.filter(
                            character_id=keeper_char_id
                        ).select_related('card')
                        if cc.pk not in situation_card_pks
                    ]

                socket.context.keeper_available_cards = await _fetch_keeper_cards()

        async def _commit_river(self, socket: LiveViewSocket[ModelContext]):
            """Save the current in-progress river to the database."""
            current = socket.context.hex_current_river
            map_id = socket.context.hex_map_id
            if not current or len(current) < 2 or not map_id:
                socket.context.hex_current_river = []
                return

            from asgiref.sync import sync_to_async as _sta

            river_to_save = list(current)

            @_sta(thread_sensitive=False)
            def _save():
                hex_map = model.objects.get(pk=map_id)
                rivers = hex_map.rivers or []
                rivers.append(river_to_save)
                hex_map.rivers = rivers
                hex_map.save(update_fields=["rivers"])

            await _save()
            socket.context.hex_current_river = []
            await self._broadcast_change(socket)

        async def _close_map_detail(self, socket: LiveViewSocket[ModelContext]):
            """Close map detail popup, releasing any locks."""
            detail_id = (socket.context.map_detail or {}).get("id", "")
            field_name = socket.context.map_detail_editing
            if detail_id and field_name:
                from .store import release_lock as _rel
                _rel("cards.situation", detail_id, field_name,
                     socket.context.session_id)
            socket.context.map_detail = {}
            socket.context.map_detail_editing = ""
            socket.context.map_detail_draft = ""

        async def _refresh_map_detail(self, socket: LiveViewSocket[ModelContext]):
            """Refresh detail popup data from DB."""
            detail_id = (socket.context.map_detail or {}).get("id", "")
            if not detail_id:
                return

            from asgiref.sync import sync_to_async as _sta
            from django.apps import apps as _apps_rd
            from .store import get_lock_holder as _glh
            from .components.editable_field import render_markdown_safe

            @_sta(thread_sensitive=False)
            def _fetch_detail():
                Situation = _apps_rd.get_model('cards', 'Situation')
                try:
                    s = Situation.objects.get(pk=detail_id)
                    data = {
                        "id": str(s.pk),
                        "name": s.name,
                        "notes": s.notes,
                        "type": s.situation_type,
                        "type_label": s.get_situation_type_display(),
                        "location": s.location,
                    }
                    # Include condensed cards for resolved situations
                    if s.resolved and s.dice:
                        from cards.models.card import get_band_for_die
                        assignments = s.assignments or {}
                        dice = s.dice
                        detail_cards = []
                        for sc in s.situation_cards.all():
                            card_id = str(sc.pk)
                            assigned_die_index = assignments.get(card_id)
                            band = ""
                            if assigned_die_index is not None and assigned_die_index < len(dice):
                                band = get_band_for_die(sc.level, dice[assigned_die_index]) or ""
                            detail_cards.append({
                                "name": sc.name,
                                "notes": sc.notes,
                                "band": band,
                            })
                        data["cards"] = detail_cards
                    return data
                except Situation.DoesNotExist:
                    return None

            data = await _fetch_detail()
            if not data:
                socket.context.map_detail = {}
                socket.context.map_detail_editing = ""
                socket.context.map_detail_draft = ""
                return

            sid = socket.context.session_id
            data["name_locked"] = (
                _glh("cards.situation", data["id"], "name") not in (None, sid)
            )
            data["notes_locked"] = (
                _glh("cards.situation", data["id"], "notes") not in (None, sid)
            )
            data["notes_html"] = (
                render_markdown_safe(data["notes"]) if data["notes"] else ""
            )
            socket.context.map_detail = data

        async def _load_map_data(self, socket: LiveViewSocket[ModelContext]):
            """Load map-specific context when viewing the HexMap model."""
            if conf.template != "map.html":
                return

            from asgiref.sync import sync_to_async as _sta
            from alive.ui import render_hex_map, render_hex_palette, render_overlay_palette, get_adjacent_hexes

            edit_mode = socket.context.hex_map_edit and socket.context.is_keeper
            show_overlays = socket.context.hex_show_overlays and socket.context.is_keeper

            # Get the HexMap instance from the game context
            game_id = socket.context.frame.get("game_id")

            @_sta(thread_sensitive=False)
            def _fetch_map():
                qs = model.objects.all()
                if game_id:
                    qs = qs.filter(game_id=game_id)
                hex_map = qs.first()
                if not hex_map and game_id:
                    hex_map = model.objects.create(name="Map", game_id=game_id)
                if hex_map:
                    return hex_map.pk, hex_map.hexes or {}, hex_map.rivers or [], hex_map.overlays or {}, hex_map.barriers or {}, hex_map.party_location or "", hex_map.party_trail or []
                return None, {}, [], {}, {}, "", []

            map_id, hexes, rivers, overlays, barriers, party_loc, party_trail = await _fetch_map()

            # Fetch timeline data (situations/notes for this game)
            timeline_entries = []
            if game_id:
                from django.apps import apps as _apps_tl

                @_sta(thread_sensitive=False)
                def _fetch_timeline():
                    Situation = _apps_tl.get_model('cards', 'Situation')
                    return list(
                        Situation.objects.filter(game_id=game_id)
                        .exclude(name="")
                        .order_by('-pk')
                        .values('pk', 'name', 'situation_type', 'location', 'notes')
                    )

                raw_entries = await _fetch_timeline()

                # Build template-ready entries with flags
                for i, e in enumerate(raw_entries):
                    is_last = i == len(raw_entries) - 1
                    entry = {
                        "id": str(e['pk']),
                        "name": e['name'],
                        "situation_type": e['situation_type'],
                        "location": e['location'],
                        "is_first": i == 0,
                        "is_last": is_last,
                        "is_current": is_last,
                    }
                    timeline_entries.append(entry)

                # Build location list for SVG hover highlights (chronological order)
                timeline_locs = [
                    (str(e['pk']), e['location'])
                    for e in reversed(raw_entries)
                ]

            socket.context.timeline_entries = timeline_entries
            socket.context.party_location = party_loc

            # Compute adjacent hexes for movement (keeper, non-edit mode)
            adjacent = None
            if socket.context.is_keeper and not edit_mode:
                if party_loc:
                    pc, pr = map(int, party_loc.split(","))
                    adjacent = get_adjacent_hexes(pc, pr)
                else:
                    # No party yet: all hexes are valid for initial placement
                    adjacent = {f"{c},{r}" for c in range(12) for r in range(12)}

            # Include the in-progress river for preview
            all_rivers = list(rivers)
            if socket.context.hex_current_river and len(socket.context.hex_current_river) >= 2:
                all_rivers.append(socket.context.hex_current_river)

            socket.context.hex_map_id = map_id
            socket.context.hex_map_svg = render_hex_map(
                hexes=hexes, rivers=all_rivers, overlays=overlays,
                barriers=barriers, edit_mode=edit_mode, show_overlays=show_overlays,
                party_location=party_loc, party_trail=party_trail[-3:],
                adjacent_hexes=adjacent,
                timeline_locations=timeline_locs if game_id else None,
            )
            if edit_mode:
                socket.context.hex_map_palette = render_hex_palette(
                    active_symbol=socket.context.hex_active_symbol,
                )
                socket.context.hex_overlay_palette = render_overlay_palette(
                    active_overlay=socket.context.hex_active_overlay,
                )

            # Refresh detail popup if open
            if socket.context.map_detail:
                await self._refresh_map_detail(socket)

        async def _load_hand_data(self, socket: LiveViewSocket[ModelContext]):
            """Load hand data for the player's character."""
            character_id = socket.context.hand_character_id
            if not character_id:
                return

            from asgiref.sync import sync_to_async as _sta
            from django.apps import apps

            game_id = socket.context.frame.get("game_id")

            @_sta(thread_sensitive=False)
            def _fetch():
                CharacterCard = apps.get_model('cards', 'CharacterCard')
                Hand = apps.get_model('cards', 'Hand')
                Situation = apps.get_model('cards', 'Situation')

                card_count = CharacterCard.objects.filter(character_id=character_id).count()

                hand = Hand.objects.filter(character_id=character_id).order_by('-id').first()
                hand_cards = []
                if hand:
                    for cc in hand.cards.select_related('card').all():
                        from cards.models.card import get_bands_for_level
                        hand_cards.append({
                            "id": str(cc.pk),
                            "name": cc.card.name,
                            "notes": cc.card.notes or "",
                            "level": cc.level,
                            "bands": get_bands_for_level(cc.level),
                        })

                # Look up active situation (latest by pk for this game)
                active_sit = None
                situation_card_pks = set()
                if game_id:
                    active_sit = Situation.objects.filter(game_id=game_id).order_by('-pk').first()
                    if active_sit:
                        situation_card_pks = set(
                            active_sit.cards.values_list('pk', flat=True)
                        )

                # Mark cards that are in the active situation
                for card in hand_cards:
                    card["in_situation"] = int(card["id"]) in situation_card_pks

                sit_dice = active_sit.dice if active_sit else []

                return card_count, hand_cards, active_sit, sit_dice

            card_count, hand_cards, active_sit, sit_dice = await _fetch()

            socket.context.hand_card_count = card_count
            socket.context.hand_drawn = len(hand_cards) > 0
            socket.context.hand_cards = hand_cards
            socket.context.hand_draw_options = list(range(1, card_count + 1))
            socket.context.hand_active_situation_id = active_sit.pk if active_sit else None
            # Only set situation_dice if not already set by _load_situation_data (which has richer data)
            if not socket.context.situation_dice:
                socket.context.situation_dice = sit_dice

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

            # Frame context from app
            from alive import _frame_context_provider
            frame_data = {}
            if _frame_context_provider:
                frame_data = await _frame_context_provider(session)

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

            socket.context = IndexContext(items=visible, frame=frame_data)
            from alive.ui import render_die_svg
            socket.context.quick_d6_svg = render_die_svg(socket.context.quick_d6, css_class="h-8 w-8")

    return IndexLiveView
