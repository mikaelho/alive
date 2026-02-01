"""Editable field component - text input or textarea with edit locking."""

from typing import Any, Protocol
from markupsafe import Markup
import markdown


class LockManager(Protocol):
    """Protocol for managing edit locks."""

    def acquire_lock(self, item_id: str, field_name: str, session_id: str) -> bool:
        """Try to acquire an edit lock. Returns True if successful."""
        ...

    def release_lock(self, item_id: str, field_name: str, session_id: str) -> bool:
        """Release an edit lock. Returns True if lock was held by this session."""
        ...

    def get_lock_holder(self, item_id: str, field_name: str) -> str | None:
        """Get the session ID holding a lock, or None if unlocked."""
        ...


class DataStore(Protocol):
    """Protocol for accessing and updating field values."""

    def get_field_value(self, item_id: str, field_name: str) -> str | None:
        """Get the current value of a field."""
        ...

    def set_field_value(self, item_id: str, field_name: str, value: str) -> bool:
        """Set the value of a field. Returns True if successful."""
        ...


def render_markdown_safe(text: str) -> Markup:
    """Render markdown text to HTML (marked as safe)."""
    return Markup(markdown.markdown(text))


def render_field_data(
    item_id: str,
    field_name: str,
    raw_value: str,
    session_id: str,
    editing: dict[str, str],
    lock_manager: LockManager,
    render_html: bool = True,
) -> dict[str, Any]:
    """
    Build the template data for an editable field.

    Returns a dict with:
    - id: the item ID
    - field: the field name
    - value: raw value
    - value_html: rendered HTML (if render_html=True)
    - is_editing: whether this session is editing
    - editing_value: current draft value if editing
    - is_locked: whether another session has the lock
    """
    key = f"{item_id}:{field_name}"
    lock_holder = lock_manager.get_lock_holder(item_id, field_name)

    is_editing = key in editing
    is_locked = lock_holder is not None and lock_holder != session_id

    data = {
        "id": item_id,
        "field": field_name,
        "value": raw_value,
        "is_editing": is_editing,
        "editing_value": editing.get(key, ""),
        "is_locked": is_locked,
    }

    if render_html:
        data["value_html"] = render_markdown_safe(raw_value)

    return data


class EditableFieldMixin:
    """
    Mixin providing editable field event handling.

    Requires the LiveView to have:
    - socket.context.session_id: str
    - socket.context.editing: dict[str, str]
    - self.lock_manager: LockManager
    - self.data_store: DataStore
    - self._refresh_view(socket): method to refresh the view after changes
    - self._broadcast_change(socket): coroutine to broadcast changes to other clients
    """

    async def handle_field_event(
        self,
        event: str,
        payload: dict[str, Any],
        socket: Any,
    ) -> bool:
        """
        Handle editable field events.

        Returns True if the event was handled, False otherwise.
        """
        session_id = socket.context.session_id

        if event == "start_edit":
            item_id = payload.get("item_id", "") or payload.get("card_id", "")
            field_name = payload.get("field", "")
            await self._handle_start_edit(socket, item_id, field_name, session_id)
            return True

        elif event == "cancel_edit":
            item_id = payload.get("item_id", "") or payload.get("card_id", "")
            field_name = payload.get("field", "")
            await self._handle_cancel_edit(socket, item_id, field_name, session_id)
            return True

        elif event == "save_edit":
            item_id = payload.get("item_id", "") or payload.get("card_id", "")
            field_name = payload.get("field", "")
            key = f"{item_id}:{field_name}"
            value = socket.context.editing.get(key, "")
            await self._handle_save_edit(socket, item_id, field_name, value, session_id)
            return True

        elif event == "update_draft":
            item_id = payload.get("item_id", "") or payload.get("card_id", "")
            field_name = payload.get("field", "")
            value_list = payload.get("value", [""])
            value = value_list[0] if isinstance(value_list, list) else value_list
            key = f"{item_id}:{field_name}"
            socket.context.editing[key] = value
            self._refresh_view(socket)
            return True

        return False

    async def _handle_start_edit(
        self, socket: Any, item_id: str, field_name: str, session_id: str
    ):
        """Handle a request to start editing a field."""
        key = f"{item_id}:{field_name}"

        if self.lock_manager.acquire_lock(item_id, field_name, session_id):
            current_value = await self.data_store.get_field_value(item_id, field_name)
            if current_value is not None:
                socket.context.editing[key] = current_value
                self._refresh_view(socket)
                await self._broadcast_change(socket)
        else:
            self._refresh_view(socket)

    async def _handle_cancel_edit(
        self, socket: Any, item_id: str, field_name: str, session_id: str
    ):
        """Handle canceling an edit."""
        key = f"{item_id}:{field_name}"

        self.lock_manager.release_lock(item_id, field_name, session_id)

        if key in socket.context.editing:
            del socket.context.editing[key]

        self._refresh_view(socket)
        await self._broadcast_change(socket)

    async def _handle_save_edit(
        self, socket: Any, item_id: str, field_name: str, value: str, session_id: str
    ):
        """Handle saving an edit."""
        key = f"{item_id}:{field_name}"

        if self.lock_manager.get_lock_holder(item_id, field_name) != session_id:
            if key in socket.context.editing:
                del socket.context.editing[key]
            self._refresh_view(socket)
            return

        await self.data_store.set_field_value(item_id, field_name, value)
        self.lock_manager.release_lock(item_id, field_name, session_id)

        if key in socket.context.editing:
            del socket.context.editing[key]

        self._refresh_view(socket)
        await self._broadcast_change(socket)
