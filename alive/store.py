"""Generic Django-backed data store for Alive models."""

from typing import Any, Type
from asgiref.sync import sync_to_async
from django.db import models


class DjangoDataStore:
    """
    Generic data store backed by Django ORM.

    Works with any Django model, providing:
    - Field get/set operations
    - Edit locking (in-memory)
    - List operations
    """

    def __init__(self, model: Type[models.Model], channel: str | None = None):
        self.model = model
        self.channel = channel or f"alive:{model._meta.label_lower}"
        # In-memory edit locks: (item_id, field_name) -> session_id
        self.edit_locks: dict[tuple[str, str], str] = {}

    # Lock management (in-memory)

    def acquire_lock(self, item_id: str, field_name: str, session_id: str) -> bool:
        """Try to acquire an edit lock. Returns True if successful."""
        key = (item_id, field_name)
        current_holder = self.edit_locks.get(key)

        if current_holder is None:
            self.edit_locks[key] = session_id
            return True
        elif current_holder == session_id:
            return True
        else:
            return False

    def release_lock(self, item_id: str, field_name: str, session_id: str) -> bool:
        """Release an edit lock. Returns True if lock was held by this session."""
        key = (item_id, field_name)
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

    def get_lock_holder(self, item_id: str, field_name: str) -> str | None:
        """Get the session ID holding a lock, or None if unlocked."""
        return self.edit_locks.get((item_id, field_name))

    # Data access (Django ORM)

    @sync_to_async
    def get_items(self) -> list[models.Model]:
        """Get all items."""
        return list(self.model.objects.all())

    @sync_to_async
    def get_item_by_id(self, item_id: str) -> models.Model | None:
        """Find an item by its ID."""
        try:
            return self.model.objects.get(pk=int(item_id))
        except (self.model.DoesNotExist, ValueError):
            return None

    @sync_to_async
    def get_field_value(self, item_id: str, field_name: str) -> Any | None:
        """Get the current value of a field."""
        try:
            item = self.model.objects.get(pk=int(item_id))
            return getattr(item, field_name, None)
        except (self.model.DoesNotExist, ValueError):
            return None

    @sync_to_async
    def set_field_value(self, item_id: str, field_name: str, value: Any) -> bool:
        """Set the value of a field. Returns True if successful."""
        try:
            item = self.model.objects.get(pk=int(item_id))
            setattr(item, field_name, value)
            item.save(update_fields=[field_name])
            return True
        except (self.model.DoesNotExist, ValueError, Exception):
            return False

    # Ordering (placeholder - not implemented yet)

    @sync_to_async
    def move_item(self, item_id: str, direction: int) -> bool:
        """Move an item up or down by direction. Not implemented yet."""
        # Would need a position field on the model to implement
        return False

    @sync_to_async
    def move_to_position(self, item_id: str, position: int) -> bool:
        """Move an item to a specific position. Not implemented yet."""
        return False


# Registry of stores by model
_stores: dict[Type[models.Model], DjangoDataStore] = {}


def get_store(model: Type[models.Model]) -> DjangoDataStore:
    """Get or create a store for a model."""
    if model not in _stores:
        _stores[model] = DjangoDataStore(model)
    return _stores[model]
