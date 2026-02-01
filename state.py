"""Shared state management for the cards application."""

from dataclasses import dataclass, field
from typing import Any
import uuid


@dataclass
class Card:
    id: str
    title: str
    content: str


@dataclass
class SharedState:
    """Global shared state accessible by all clients."""

    cards: list[Card] = field(default_factory=list)
    # Maps (card_id, field_name) -> session_id
    edit_locks: dict[tuple[str, str], str] = field(default_factory=dict)

    def acquire_lock(self, card_id: str, field_name: str, session_id: str) -> bool:
        """Try to acquire an edit lock. Returns True if successful."""
        key = (card_id, field_name)
        current_holder = self.edit_locks.get(key)

        if current_holder is None:
            self.edit_locks[key] = session_id
            return True
        elif current_holder == session_id:
            # Already holding the lock
            return True
        else:
            # Someone else has the lock
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

    def get_card_by_id(self, card_id: str) -> Card | None:
        """Find a card by its ID."""
        for card in self.cards:
            if card.id == card_id:
                return card
        return None

    def get_card_index(self, card_id: str) -> int | None:
        """Get the index of a card by its ID."""
        for i, card in enumerate(self.cards):
            if card.id == card_id:
                return i
        return None

    def move_card(self, card_id: str, direction: int) -> bool:
        """Move a card up (-1) or down (+1). Returns True if moved."""
        index = self.get_card_index(card_id)
        if index is None:
            return False

        new_index = index + direction
        if new_index < 0 or new_index >= len(self.cards):
            return False

        # Swap cards
        self.cards[index], self.cards[new_index] = self.cards[new_index], self.cards[index]
        return True

    def reorder_card(self, card_id: str, target_id: str, insert_after: bool) -> bool:
        """Move a card to before or after another card. Returns True if moved."""
        source_index = self.get_card_index(card_id)
        target_index = self.get_card_index(target_id)

        if source_index is None or target_index is None:
            return False

        if source_index == target_index:
            return False

        # Remove card from current position
        card = self.cards.pop(source_index)

        # Adjust target index if source was before target
        if source_index < target_index:
            target_index -= 1

        # Insert at new position
        if insert_after:
            self.cards.insert(target_index + 1, card)
        else:
            self.cards.insert(target_index, card)

        return True

    def move_to_position(self, card_id: str, position: int) -> bool:
        """Move a card to a specific position (0-indexed). Returns True if moved."""
        source_index = self.get_card_index(card_id)
        if source_index is None:
            return False

        # Clamp position to valid range
        position = max(0, min(position, len(self.cards) - 1))

        # If already at target position, no change needed
        if source_index == position:
            return False

        # Remove card from current position
        card = self.cards.pop(source_index)

        # Insert at new position
        self.cards.insert(position, card)
        return True

    def update_card_field(self, card_id: str, field_name: str, value: str) -> bool:
        """Update a card's field value. Returns True if successful."""
        card = self.get_card_by_id(card_id)
        if card is None:
            return False

        if field_name == "title":
            card.title = value
        elif field_name == "content":
            card.content = value
        else:
            return False

        return True

    # DataStore protocol methods
    def get_field_value(self, item_id: str, field_name: str) -> str | None:
        """Get the current value of a field."""
        card = self.get_card_by_id(item_id)
        if card is None:
            return None
        if field_name == "title":
            return card.title
        elif field_name == "content":
            return card.content
        return None

    def set_field_value(self, item_id: str, field_name: str, value: str) -> bool:
        """Set the value of a field. Returns True if successful."""
        return self.update_card_field(item_id, field_name, value)


# Initialize global state with 3 sample cards
shared_state = SharedState(
    cards=[
        Card(
            id=str(uuid.uuid4()),
            title="Welcome",
            content="This is the **first** card. Try editing me!",
        ),
        Card(
            id=str(uuid.uuid4()),
            title="Features",
            content="- Real-time sync\n- Markdown support\n- Edit locking",
        ),
        Card(
            id=str(uuid.uuid4()),
            title="Instructions",
            content="Click any text to edit. Changes sync to all users.",
        ),
    ]
)
