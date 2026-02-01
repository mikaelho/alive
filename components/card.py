"""Card component - a card with editable title and content fields."""

from typing import Any, Protocol

from .editable_field import render_field_data, LockManager


class Card(Protocol):
    """Protocol for a card data object."""

    id: str
    title: str
    content: str


def render_card_data(
    card: Card,
    session_id: str,
    editing: dict[str, str],
    lock_manager: LockManager,
) -> dict[str, Any]:
    """
    Build the template data for a card with editable fields.

    Returns a dict with all card data including field states.
    """
    # Convert ID to string for consistency (Django uses int IDs)
    card_id = str(card.id)

    title_data = render_field_data(
        item_id=card_id,
        field_name="title",
        raw_value=card.title,
        session_id=session_id,
        editing=editing,
        lock_manager=lock_manager,
        render_html=True,
    )

    content_data = render_field_data(
        item_id=card_id,
        field_name="content",
        raw_value=card.content,
        session_id=session_id,
        editing=editing,
        lock_manager=lock_manager,
        render_html=True,
    )

    return {
        "id": card_id,
        "title": card.title,
        "title_html": title_data["value_html"],
        "title_editing": title_data["is_editing"],
        "title_editing_value": title_data["editing_value"],
        "title_locked": title_data["is_locked"],
        "content": card.content,
        "content_html": content_data["value_html"],
        "content_editing": content_data["is_editing"],
        "content_editing_value": content_data["editing_value"],
        "content_locked": content_data["is_locked"],
    }


class CardMixin:
    """
    Mixin providing card-specific event handling (reordering).

    Requires the LiveView to have:
    - self.card_store: object with move_card() and reorder_card() methods
    - self._refresh_view(socket): method to refresh the view after changes
    - self._broadcast_change(socket): coroutine to broadcast changes to other clients
    """

    async def handle_card_event(
        self,
        event: str,
        payload: dict[str, Any],
        socket: Any,
    ) -> bool:
        """
        Handle card-specific events.

        Returns True if the event was handled, False otherwise.
        """
        if event == "move_card":
            card_id = payload.get("card_id", "")
            direction = int(payload.get("direction", 0))
            if self.card_store.move_card(card_id, direction):
                self._refresh_view(socket)
                await self._broadcast_change(socket)
            return True

        if event == "reorder_card":
            card_id = payload.get("card_id", "")
            target_id = payload.get("target_id", "")
            insert_after = payload.get("insert_after", "false") == "true"
            if self.card_store.reorder_card(card_id, target_id, insert_after):
                self._refresh_view(socket)
                await self._broadcast_change(socket)
            return True

        if event == "reorder_to_position":
            card_id = payload.get("card_id", "")
            position = int(payload.get("position", 0))
            result = await self.card_store.move_to_position(card_id, position)
            if result:
                self._refresh_view(socket)
                await self._broadcast_change(socket)
            return True

        return False
