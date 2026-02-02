"""Generic Django-backed data store for Alive models."""

from typing import Any, Type
from asgiref.sync import sync_to_async
from django.db import models

# Use thread_sensitive=False to avoid deadlock when called from handle_info
def async_db(func):
    """Wrapper for sync_to_async that avoids deadlocks."""
    return sync_to_async(func, thread_sensitive=False)


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

    @async_db
    def get_items(self, filters: dict[str, Any] | None = None) -> list[models.Model]:
        """Get all items, optionally filtered."""
        qs = self.model.objects.all()
        if filters:
            qs = qs.filter(**filters)
        return list(qs)

    @async_db
    def get_item_by_id(self, item_id: str) -> models.Model | None:
        """Find an item by its ID."""
        try:
            return self.model.objects.get(pk=int(item_id))
        except (self.model.DoesNotExist, ValueError):
            return None

    @async_db
    def get_field_value(self, item_id: str, field_name: str) -> Any | None:
        """Get the current value of a field."""
        try:
            item = self.model.objects.get(pk=int(item_id))
            return getattr(item, field_name, None)
        except (self.model.DoesNotExist, ValueError):
            return None

    @async_db
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

    @async_db
    def move_item(self, item_id: str, direction: int) -> bool:
        """Move an item up or down by direction. Not implemented yet."""
        # Would need a position field on the model to implement
        return False

    @async_db
    def move_to_position(self, item_id: str, position: int) -> bool:
        """Move an item to a specific position. Not implemented yet."""
        return False

    @async_db
    def create_item(self, field_values: dict[str, Any]) -> models.Model | None:
        """Create a new item with the given field values."""
        try:
            item = self.model(**field_values)
            item.full_clean()
            item.save()
            return item
        except Exception as e:
            print(f"[alive] Error creating item: {e}")
            return None

    @async_db
    def add_to_relation(self, item: models.Model, relation_field: str, related_pk: Any) -> bool:
        """Add an item to a M2M relation on the related model."""
        try:
            # relation_field is like "recipes" - the related_name on the M2M field
            # We need to find which model has the M2M field pointing to this model
            for field in self.model._meta.get_fields():
                if field.name == relation_field:
                    # This is a reverse M2M relation
                    if hasattr(field, 'related_model') and hasattr(field, 'field'):
                        related_model = field.related_model
                        related_obj = related_model.objects.get(pk=related_pk)
                        # field.field is the actual M2M field on the related model
                        m2m_field_name = field.field.name
                        getattr(related_obj, m2m_field_name).add(item)
                        return True
            return False
        except Exception as e:
            print(f"[alive] Error adding to relation: {e}")
            return False


# Registry of stores by model
_stores: dict[Type[models.Model], DjangoDataStore] = {}


def get_store(model: Type[models.Model]) -> DjangoDataStore:
    """Get or create a store for a model."""
    if model not in _stores:
        _stores[model] = DjangoDataStore(model)
    return _stores[model]
