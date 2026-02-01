"""Django-backed data store for cards."""

from typing import Any
from asgiref.sync import sync_to_async

from .models import Card


class DjangoCardStore:
    """
    Data store backed by Django ORM.

    Implements the same interface as the in-memory SharedState,
    allowing the LiveView to work with either backend.
    """

    def __init__(self, pubsub=None, channel: str = "cards_channel"):
        self.pubsub = pubsub
        self.channel = channel
        # In-memory edit locks (card_id, field_name) -> session_id
        self.edit_locks: dict[tuple[str, str], str] = {}

    def set_pubsub(self, pubsub):
        """Set the pub/sub reference (called after PyView app is created)."""
        self.pubsub = pubsub

    # Lock management (in-memory, same as before)

    def acquire_lock(self, card_id: str, field_name: str, session_id: str) -> bool:
        """Try to acquire an edit lock. Returns True if successful."""
        key = (card_id, field_name)
        current_holder = self.edit_locks.get(key)

        if current_holder is None:
            self.edit_locks[key] = session_id
            return True
        elif current_holder == session_id:
            return True
        else:
            return False

    def release_lock(self, card_id: str, field_name: str, session_id: str) -> bool:
        """Release an edit lock. Returns True if lock was held by this session."""
        key = (card_id, field_name)
        current_holder = self.edit_locks.get(key)

        if current_holder == session_id:
            del self.edit_locks[key]
            return True
        return False

    def release_all_locks(self, session_id: str) -> list[tuple[str, str]]:
        """Release all locks held by a session. Returns list of released keys."""
        released = []
        keys_to_remove = [
            key for key, holder in self.edit_locks.items()
            if holder == session_id
        ]
        for key in keys_to_remove:
            del self.edit_locks[key]
            released.append(key)
        return released

    def get_lock_holder(self, card_id: str, field_name: str) -> str | None:
        """Get the session ID holding a lock, or None if unlocked."""
        return self.edit_locks.get((card_id, field_name))

    # Card access (Django ORM)

    @sync_to_async
    def get_cards(self) -> list[Card]:
        """Get all cards."""
        return list(Card.objects.all())

    @sync_to_async
    def get_card_by_id(self, card_id: str) -> Card | None:
        """Find a card by its ID."""
        try:
            return Card.objects.get(id=int(card_id))
        except (Card.DoesNotExist, ValueError):
            return None

    @sync_to_async
    def get_field_value(self, item_id: str, field_name: str) -> str | None:
        """Get the current value of a field."""
        try:
            card = Card.objects.get(id=int(item_id))
            return getattr(card, field_name, None)
        except (Card.DoesNotExist, ValueError):
            return None

    @sync_to_async
    def set_field_value(self, item_id: str, field_name: str, value: str) -> bool:
        """Set the value of a field. Returns True if successful."""
        try:
            card = Card.objects.get(id=int(item_id))
            setattr(card, field_name, value)
            card.save(update_fields=[field_name])
            return True
        except (Card.DoesNotExist, ValueError, Exception):
            return False

    # Ordering (simplified - no persistence for now)

    @sync_to_async
    def move_to_position(self, card_id: str, position: int) -> bool:
        """
        Move a card to a specific position.

        Note: For now, this doesn't persist ordering since we're using
        created_at ordering. Returns False to indicate no change.
        """
        # TODO: Implement persistent ordering later
        return False


# Global store instance (will be configured with pubsub in app.py)
card_store = DjangoCardStore()
