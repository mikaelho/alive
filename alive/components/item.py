"""Generic item component for rendering Django model instances."""

from typing import Any, Sequence

from django.db import models as django_models

from .editable_field import render_field_data, LockManager


def render_item_data(
    item: Any,
    fields: Sequence[str],
    session_id: str,
    editing: dict[str, str],
    lock_manager: LockManager,
    title_field: str | None = None,
    content_fields: Sequence[str] | None = None,
    fk_field_names: Sequence[str] | None = None,
    tag_data: list[dict] | None = None,
    inline_sections: list[dict] | None = None,
    compact_fields: Sequence[str] = (),
) -> dict[str, Any]:
    """
    Build the template data for any model instance with editable fields.

    Args:
        item: The model instance
        fields: List of field names to include
        session_id: Current user's session ID
        editing: Dict of field keys being edited -> current draft value
        lock_manager: Lock manager for edit locking
        title_field: Which field to use as the title (optional)
        content_fields: Fields to show in the body (optional, defaults to non-title fields)
        fk_field_names: List of FK field names (optional, for FK picker support)

    Returns:
        Dict with item data including field states for each field.
    """
    fk_field_names = fk_field_names or []
    item_id = str(item.pk)

    data = {
        "id": item_id,
        "fields": {},
    }

    # Build a map of field names to verbose labels
    field_labels = {}
    for field in item._meta.get_fields():
        if hasattr(field, 'name') and hasattr(field, 'verbose_name'):
            field_labels[field.name] = field.verbose_name.title()

    for field_name in fields:
        raw_value = getattr(item, field_name, "")
        is_fk = field_name in fk_field_names
        fk_pk = None

        if raw_value is None:
            raw_value = ""
        elif is_fk:
            # For FK fields, store the pk before converting to string
            fk_pk = str(raw_value.pk) if hasattr(raw_value, 'pk') else ""
            raw_value = str(raw_value)

        # Convert non-string values to string for display
        if not isinstance(raw_value, str):
            raw_value = str(raw_value)

        field_data = render_field_data(
            item_id=item_id,
            field_name=field_name,
            raw_value=raw_value,
            session_id=session_id,
            editing=editing,
            lock_manager=lock_manager,
            render_html=True,
        )

        # Add FK-specific data and label
        field_data["is_fk"] = is_fk
        field_data["fk_pk"] = fk_pk
        field_data["label"] = field_labels.get(field_name, field_name.replace('_', ' ').title())

        data["fields"][field_name] = field_data

        # Also add flat access for convenience in templates
        data[f"{field_name}"] = raw_value
        data[f"{field_name}_html"] = field_data["value_html"]
        data[f"{field_name}_editing"] = field_data["is_editing"]
        data[f"{field_name}_editing_value"] = field_data["editing_value"]
        data[f"{field_name}_locked"] = field_data["is_locked"]

    # Set title field data with standard names for template access
    if title_field and title_field in fields:
        title_data = data["fields"][title_field]
        data["title_field_name"] = title_field
        data["title_html"] = title_data["value_html"]
        data["title_editing"] = title_data["is_editing"]
        data["title_editing_value"] = title_data["editing_value"]
        data["title_locked"] = title_data["is_locked"]

    # Build compact fields data (displayed inline in the title row)
    compact_set = set(compact_fields)
    compact_fields_data = []
    for field_name in compact_fields:
        if field_name in data["fields"]:
            field_info = data["fields"][field_name].copy()
            field_info["name"] = field_name
            compact_fields_data.append(field_info)
    data["compact_fields_data"] = compact_fields_data
    data["has_compact_fields"] = bool(compact_fields_data)

    # Build content fields list with data for template iteration
    if content_fields is None:
        content_fields = [f for f in fields if f != title_field]

    content_fields_data = []
    for field_name in content_fields:
        if field_name in compact_set:
            continue
        if field_name in data["fields"]:
            field_info = data["fields"][field_name].copy()
            field_info["name"] = field_name
            try:
                django_field = item._meta.get_field(field_name)
                field_info["is_collapsible"] = isinstance(django_field, django_models.TextField)
            except Exception:
                field_info["is_collapsible"] = False
            content_fields_data.append(field_info)

    data["content_fields_data"] = content_fields_data

    # Tag data
    data["tags_data"] = tag_data or []
    data["has_tags"] = bool(tag_data)

    # Inline sections
    data["inline_sections"] = inline_sections or []
    data["has_inline"] = bool(inline_sections)

    return data


class ItemMixin:
    """
    Mixin providing item-specific event handling (reordering).

    Requires the LiveView to have:
    - self.data_store: object with move_to_position() method
    - self._refresh_view(socket): method to refresh the view after changes
    - self._broadcast_change(socket): coroutine to broadcast changes
    """

    async def handle_item_event(
        self,
        event: str,
        payload: dict[str, Any],
        socket: Any,
    ) -> bool:
        """
        Handle item-specific events (e.g., reordering).

        Returns True if the event was handled, False otherwise.
        """
        if event == "move_item":
            item_id = payload.get("item_id", "") or payload.get("card_id", "")
            direction = int(payload.get("direction", 0))
            result = await self.data_store.move_item(item_id, direction)
            if result:
                self._refresh_view(socket)
                await self._broadcast_change(socket)
            return True

        if event == "reorder_to_position":
            item_id = payload.get("item_id", "") or payload.get("card_id", "")
            position = int(payload.get("position", 0))
            result = await self.data_store.move_to_position(item_id, position)
            if result:
                self._refresh_view(socket)
                await self._broadcast_change(socket)
            return True

        return False
