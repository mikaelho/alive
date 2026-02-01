"""Cards LiveView - manual view for the collaborative cards application.

This is the original hand-crafted view. Compare with /alive/card/ which
uses the auto-generated view from the alive module.
"""

from dataclasses import dataclass, field
from typing import Any
import uuid

from pyview import LiveView, LiveViewSocket, is_connected
from pyview.events import InfoEvent

from cards.store import card_store
from components import EditableFieldMixin, CardMixin, render_card_data


@dataclass
class CardsContext:
    """Context for the cards view."""

    cards: list[dict] = field(default_factory=list)
    session_id: str = ""
    editing: dict[str, str] = field(default_factory=dict)


class CardsLiveView(EditableFieldMixin, CardMixin, LiveView[CardsContext]):
    """LiveView for the collaborative cards page."""

    lock_manager = card_store
    data_store = card_store
    card_store = card_store

    async def mount(self, socket: LiveViewSocket[CardsContext], session: dict[str, Any]):
        session_id = session.get("id")
        if not session_id:
            session_id = str(uuid.uuid4())
            session["id"] = session_id

        editing: dict[str, str] = {}
        cards_data = await self._build_cards_data(session_id, editing)

        socket.context = CardsContext(
            cards=cards_data,
            session_id=session_id,
            editing=editing,
        )

        if is_connected(socket):
            await socket.subscribe("cards_channel")

    async def disconnect(self, socket: LiveViewSocket[CardsContext]):
        """Clean up locks when client disconnects."""
        session_id = socket.context.session_id
        released = card_store.release_all_locks(session_id)

        if released:
            await socket.broadcast("cards_channel", {
                "action": "locks_released",
                "keys": [f"{card_id}:{field}" for card_id, field in released],
            })

    async def handle_event(self, event: str, payload: dict[str, Any], socket: LiveViewSocket[CardsContext]):
        if await self.handle_field_event(event, payload, socket):
            return
        if await self.handle_card_event(event, payload, socket):
            return

    async def handle_info(self, event: InfoEvent, socket: LiveViewSocket[CardsContext]):
        """Handle pub/sub messages from other clients or Django signals."""
        if event.name != "cards_channel":
            return

        data = event.payload
        action = data.get("action", "")

        if action in ("state_changed", "locks_released", "card_created", "card_deleted"):
            await self._refresh_view_async(socket)
        elif action == "conflict":
            conflict_key = data.get("key", "")
            if conflict_key in socket.context.editing:
                del socket.context.editing[conflict_key]
            await self._refresh_view_async(socket)

    def _refresh_view(self, socket: LiveViewSocket[CardsContext]):
        """Sync refresh - schedules async refresh."""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._refresh_view_async(socket))
        except RuntimeError:
            pass

    async def _refresh_view_async(self, socket: LiveViewSocket[CardsContext]):
        """Async refresh the cards data in context."""
        socket.context.cards = await self._build_cards_data(
            socket.context.session_id, socket.context.editing
        )

    async def _broadcast_change(self, socket: LiveViewSocket[CardsContext]):
        """Broadcast state change to other clients."""
        await socket.broadcast("cards_channel", {"action": "state_changed"})

    async def _build_cards_data(self, session_id: str, editing: dict[str, str]) -> list[dict]:
        """Build the cards data for the template."""
        cards = await card_store.get_cards()
        return [
            render_card_data(card, session_id, editing, card_store)
            for card in cards
        ]
