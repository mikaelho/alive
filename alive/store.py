"""Generic Django-backed data store for Alive models."""

from typing import Any, Type
from asgiref.sync import sync_to_async
from django.db import models
from django.db.models import Max

# Use thread_sensitive=False to avoid deadlock when called from handle_info
def async_db(func):
    """Wrapper for sync_to_async that avoids deadlocks."""
    return sync_to_async(func, thread_sensitive=False)


# Global lock registry: (model_label, item_id, field_name) -> session_id
# Shared across all stores so locks work regardless of which view edits a field.
_edit_locks: dict[tuple[str, str, str], str] = {}


def acquire_lock(model_label: str, item_id: str, field_name: str, session_id: str) -> bool:
    """Try to acquire an edit lock. Returns True if successful."""
    key = (model_label, item_id, field_name)
    current_holder = _edit_locks.get(key)
    if current_holder is None:
        _edit_locks[key] = session_id
        return True
    elif current_holder == session_id:
        return True
    return False


def release_lock(model_label: str, item_id: str, field_name: str, session_id: str) -> bool:
    """Release an edit lock. Returns True if lock was held by this session."""
    key = (model_label, item_id, field_name)
    if _edit_locks.get(key) == session_id:
        del _edit_locks[key]
        return True
    return False


def get_lock_holder(model_label: str, item_id: str, field_name: str) -> str | None:
    """Get the session ID holding a lock, or None if unlocked."""
    return _edit_locks.get((model_label, item_id, field_name))


def release_all_locks(session_id: str) -> list[tuple[str, str, str]]:
    """Release all locks held by a session. Returns list of (model_label, item_id, field_name)."""
    released = []
    keys_to_remove = [
        key for key, holder in _edit_locks.items()
        if holder == session_id
    ]
    for key in keys_to_remove:
        del _edit_locks[key]
        released.append(key)
    return released


class DjangoDataStore:
    """
    Generic data store backed by Django ORM.

    Works with any Django model, providing:
    - Field get/set operations
    - List operations
    """

    def __init__(self, model: Type[models.Model], channel: str | None = None):
        self.model = model
        self.channel = channel or f"alive:{model._meta.label_lower}"
        self.model_label = model._meta.label_lower

    # Lock convenience methods (delegate to module-level functions)

    def acquire_lock(self, item_id: str, field_name: str, session_id: str) -> bool:
        return acquire_lock(self.model_label, item_id, field_name, session_id)

    def release_lock(self, item_id: str, field_name: str, session_id: str) -> bool:
        return release_lock(self.model_label, item_id, field_name, session_id)

    def get_lock_holder(self, item_id: str, field_name: str) -> str | None:
        return get_lock_holder(self.model_label, item_id, field_name)

    def release_all_locks(self, session_id: str) -> list[tuple[str, str, str]]:
        return release_all_locks(session_id)

    # Data access (Django ORM)

    @async_db
    def get_items(self, filters: dict[str, Any] | None = None, qs_hook=None) -> list[models.Model]:
        """Get all items, optionally filtered."""
        qs = self.model.objects.all()
        # Eagerly load FK relations to avoid lazy queries in async context
        fk_fields = [
            f.name for f in self.model._meta.get_fields()
            if isinstance(f, models.ForeignKey)
        ]
        if fk_fields:
            qs = qs.select_related(*fk_fields)
        if filters:
            qs = qs.filter(**filters)
        if qs_hook:
            qs = qs_hook(qs)
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
            # Convert FK fields: pass as field_id=int(pk) instead of field=pk
            resolved = {}
            for key, value in field_values.items():
                try:
                    field = self.model._meta.get_field(key)
                except Exception:
                    resolved[key] = value
                    continue
                if isinstance(field, models.ForeignKey):
                    resolved[f"{key}_id"] = int(value) if value else None
                else:
                    resolved[key] = value
            item = self.model(**resolved)
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

    @async_db
    def delete_item(self, item_id: str) -> bool:
        """Delete an item by its ID. Returns True if successful."""
        try:
            item = self.model.objects.get(pk=int(item_id))
            item.delete()
            return True
        except (self.model.DoesNotExist, ValueError, Exception) as e:
            print(f"[alive] Error deleting item: {e}")
            return False

    @async_db
    def get_unlinked_items(self, relation_field: str, related_pk: Any) -> list[models.Model]:
        """Get items NOT linked to a specific related object via a M2M relation."""
        try:
            # Get all items
            all_items = set(self.model.objects.all().values_list('pk', flat=True))

            # Get items that ARE linked
            linked_items = set(
                self.model.objects.filter(**{f"{relation_field}__pk": related_pk})
                .values_list('pk', flat=True)
            )

            # Return unlinked items
            unlinked_pks = all_items - linked_items
            return list(self.model.objects.filter(pk__in=unlinked_pks))
        except Exception as e:
            print(f"[alive] Error getting unlinked items: {e}")
            return []

    @async_db
    def add_items_to_relation(self, item_pks: list[str], relation_field: str, related_pk: Any) -> bool:
        """Add multiple items to a M2M relation."""
        try:
            for field in self.model._meta.get_fields():
                if field.name == relation_field:
                    if hasattr(field, 'related_model') and hasattr(field, 'field'):
                        related_model = field.related_model
                        related_obj = related_model.objects.get(pk=related_pk)
                        m2m_field_name = field.field.name
                        items = self.model.objects.filter(pk__in=[int(pk) for pk in item_pks])
                        getattr(related_obj, m2m_field_name).add(*items)
                        return True
            return False
        except Exception as e:
            print(f"[alive] Error adding items to relation: {e}")
            return False

    @async_db
    def remove_from_relation(self, item_pk: str, relation_field: str, related_pk: Any) -> bool:
        """Remove an item from a M2M relation (unlink, not delete)."""
        try:
            for field in self.model._meta.get_fields():
                if field.name == relation_field:
                    if hasattr(field, 'related_model') and hasattr(field, 'field'):
                        related_model = field.related_model
                        related_obj = related_model.objects.get(pk=related_pk)
                        m2m_field_name = field.field.name
                        item = self.model.objects.get(pk=int(item_pk))
                        getattr(related_obj, m2m_field_name).remove(item)
                        return True
            return False
        except Exception as e:
            print(f"[alive] Error removing from relation: {e}")
            return False

    @async_db
    def get_fk_choices_for_create(self, field_name: str) -> list[tuple]:
        """Get FK choices as tuples (pk, str) for creation form select."""
        try:
            field = self.model._meta.get_field(field_name)
            if not hasattr(field, 'related_model'):
                return []
            related_model = field.related_model
            return [(obj.pk, str(obj)) for obj in related_model.objects.all()[:100]]
        except Exception as e:
            print(f"[alive] Error getting FK choices for create: {e}")
            return []

    @async_db
    def get_fk_choices(self, field_name: str, filter_text: str = "") -> list[dict]:
        """Get available FK choices, optionally filtered by text."""
        try:
            # Find the FK field
            field = self.model._meta.get_field(field_name)
            if not hasattr(field, 'related_model'):
                return []

            related_model = field.related_model
            qs = related_model.objects.all()

            # Filter by text if provided
            if filter_text:
                # Try to filter on common text fields
                filter_text_lower = filter_text.lower()
                # Get all objects and filter by str() representation
                items = []
                for obj in qs:
                    if filter_text_lower in str(obj).lower():
                        items.append({"id": str(obj.pk), "title": str(obj)})
                return items
            else:
                return [{"id": str(obj.pk), "title": str(obj)} for obj in qs]
        except Exception as e:
            print(f"[alive] Error getting FK choices: {e}")
            return []

    @async_db
    def set_fk_value(self, item_id: str, field_name: str, related_pk: str | None) -> bool:
        """Set a FK field to a specific value (or None)."""
        try:
            item = self.model.objects.get(pk=int(item_id))

            if related_pk is None or related_pk == "":
                # Set to None (only if field is nullable)
                setattr(item, field_name, None)
            else:
                # Get the related field to find the related model
                field = self.model._meta.get_field(field_name)
                related_model = field.related_model
                related_obj = related_model.objects.get(pk=int(related_pk))
                setattr(item, field_name, related_obj)

            item.save(update_fields=[field_name])
            return True
        except Exception as e:
            print(f"[alive] Error setting FK value: {e}")
            return False

    # Tag operations

    def _is_tag_field_m2m(self, tag_field_name: str) -> bool:
        """Check if a tag field is M2M (True) or FK (False)."""
        field = self.model._meta.get_field(tag_field_name)
        return isinstance(field, models.ManyToManyField)

    def _get_m2m_through_info(self, tag_field_name: str) -> dict | None:
        """Get through model info for an ordered M2M field. Returns None if not ordered."""
        field = self.model._meta.get_field(tag_field_name)
        if not isinstance(field, models.ManyToManyField):
            return None
        through = field.remote_field.through
        if not hasattr(through, 'position'):
            return None
        # Find the FK field names on the through model
        source_fk = None
        target_fk = None
        for f in through._meta.get_fields():
            if isinstance(f, models.ForeignKey):
                if f.related_model == self.model:
                    source_fk = f.name
                elif f.related_model == field.related_model:
                    target_fk = f.name
        if source_fk and target_fk:
            return {"through": through, "source_fk": source_fk, "target_fk": target_fk}
        return None

    @async_db
    def get_tags_for_item(self, item_id: str, tag_field_name: str) -> list[dict]:
        """Get tags currently attached to an item, ordered by position if available."""
        try:
            item = self.model.objects.select_related().get(pk=int(item_id))
            if self._is_tag_field_m2m(tag_field_name):
                through_info = self._get_m2m_through_info(tag_field_name)
                if through_info:
                    # Ordered M2M: query through model directly
                    entries = (
                        through_info["through"].objects
                        .filter(**{through_info["source_fk"]: item})
                        .select_related(through_info["target_fk"])
                        .order_by('position')
                    )
                    return [
                        {"id": str(getattr(e, through_info["target_fk"]).pk),
                         "title": str(getattr(e, through_info["target_fk"]))}
                        for e in entries
                    ]
                else:
                    m2m_manager = getattr(item, tag_field_name)
                    return [{"id": str(tag.pk), "title": str(tag)} for tag in m2m_manager.all()]
            else:
                # FK field - single value
                related = getattr(item, tag_field_name)
                if related is not None:
                    return [{"id": str(related.pk), "title": str(related)}]
                return []
        except Exception as e:
            print(f"[alive] Error getting tags for item: {e}")
            return []

    @async_db
    def get_available_tags(
        self,
        item_id: str,
        tag_field_name: str,
        scope_model=None,
        scope_pk=None,
        scope_m2m_field=None,
        search_text: str = "",
    ) -> list[dict]:
        """Get available tags, optionally scoped and filtered."""
        try:
            item = self.model.objects.select_related().get(pk=int(item_id))
            is_m2m = self._is_tag_field_m2m(tag_field_name)

            if is_m2m:
                attached_pks = set(
                    getattr(item, tag_field_name).values_list("pk", flat=True)
                )
            else:
                related = getattr(item, tag_field_name)
                attached_pks = {related.pk} if related is not None else set()

            # Determine the pool of tags
            if scope_model and scope_pk and scope_m2m_field:
                scope_obj = scope_model.objects.get(pk=int(scope_pk))
                pool = getattr(scope_obj, scope_m2m_field).all()
            else:
                field = self.model._meta.get_field(tag_field_name)
                tag_model = field.related_model
                pool = tag_model.objects.all()

            results = []
            search_lower = search_text.lower() if search_text else ""
            for tag in pool:
                title = str(tag)
                if search_lower and search_lower not in title.lower():
                    continue
                results.append({
                    "id": str(tag.pk),
                    "title": title,
                    "attached": tag.pk in attached_pks,
                })
            return results
        except Exception as e:
            print(f"[alive] Error getting available tags: {e}")
            return []

    @async_db
    def toggle_tag(self, item_id: str, tag_field_name: str, tag_pk: str) -> bool:
        """Toggle a tag on/off for an item. For FK fields, sets or clears the value."""
        try:
            item = self.model.objects.select_related().get(pk=int(item_id))
            tag_pk_int = int(tag_pk)

            if self._is_tag_field_m2m(tag_field_name):
                m2m = getattr(item, tag_field_name)
                if m2m.filter(pk=tag_pk_int).exists():
                    m2m.remove(tag_pk_int)
                else:
                    through_info = self._get_m2m_through_info(tag_field_name)
                    if through_info:
                        max_pos = (
                            through_info["through"].objects
                            .filter(**{through_info["source_fk"]: item})
                            .aggregate(Max('position'))['position__max']
                        )
                        next_pos = (max_pos + 1) if max_pos is not None else 0
                        m2m.add(tag_pk_int, through_defaults={'position': next_pos})
                    else:
                        m2m.add(tag_pk_int)
            else:
                # FK: toggle - set if different, clear if same
                current = getattr(item, tag_field_name)
                if current is not None and current.pk == tag_pk_int:
                    setattr(item, tag_field_name, None)
                else:
                    field = self.model._meta.get_field(tag_field_name)
                    tag_obj = field.related_model.objects.get(pk=tag_pk_int)
                    setattr(item, tag_field_name, tag_obj)
                item.save(update_fields=[tag_field_name])
            return True
        except Exception as e:
            print(f"[alive] Error toggling tag: {e}")
            return False

    @async_db
    def remove_tag(self, item_id: str, tag_field_name: str, tag_pk: str) -> bool:
        """Remove a tag from an item."""
        try:
            item = self.model.objects.get(pk=int(item_id))
            if self._is_tag_field_m2m(tag_field_name):
                getattr(item, tag_field_name).remove(int(tag_pk))
            else:
                setattr(item, tag_field_name, None)
                item.save(update_fields=[tag_field_name])
            return True
        except Exception as e:
            print(f"[alive] Error removing tag: {e}")
            return False

    @async_db
    def create_tag(
        self,
        tag_field_name: str,
        field_values: dict,
        item_id: str,
        scope_model=None,
        scope_pk=None,
        scope_m2m_field=None,
    ) -> Any:
        """Create a new tag, add to item, and optionally add to scope."""
        try:
            field = self.model._meta.get_field(tag_field_name)
            tag_model = field.related_model
            tag = tag_model(**field_values)
            tag.full_clean()
            tag.save()

            # Add to item
            item = self.model.objects.get(pk=int(item_id))
            if self._is_tag_field_m2m(tag_field_name):
                through_info = self._get_m2m_through_info(tag_field_name)
                if through_info:
                    max_pos = (
                        through_info["through"].objects
                        .filter(**{through_info["source_fk"]: item})
                        .aggregate(Max('position'))['position__max']
                    )
                    next_pos = (max_pos + 1) if max_pos is not None else 0
                    getattr(item, tag_field_name).add(tag, through_defaults={'position': next_pos})
                else:
                    getattr(item, tag_field_name).add(tag)
            else:
                setattr(item, tag_field_name, tag)
                item.save(update_fields=[tag_field_name])

            # Add to scope
            if scope_model and scope_pk and scope_m2m_field:
                scope_obj = scope_model.objects.get(pk=int(scope_pk))
                getattr(scope_obj, scope_m2m_field).add(tag)

            return tag
        except Exception as e:
            print(f"[alive] Error creating tag: {e}")
            return None

    @async_db
    def reorder_tag(self, item_id: str, tag_field_name: str, tag_pk: str, new_position: int) -> bool:
        """Move a tag to a new position in an ordered M2M."""
        try:
            through_info = self._get_m2m_through_info(tag_field_name)
            if not through_info:
                return False
            item = self.model.objects.get(pk=int(item_id))
            through = through_info["through"]
            source_fk = through_info["source_fk"]
            target_fk = through_info["target_fk"]
            entries = list(
                through.objects.filter(**{source_fk: item}).order_by('position')
            )
            # Find the moved entry
            moved = next(
                (e for e in entries if getattr(e, f"{target_fk}_id") == int(tag_pk)),
                None,
            )
            if not moved:
                return False
            entries.remove(moved)
            entries.insert(new_position, moved)
            for i, entry in enumerate(entries):
                if entry.position != i:
                    entry.position = i
                    entry.save(update_fields=['position'])
            return True
        except Exception as e:
            print(f"[alive] Error reordering tag: {e}")
            return False

    def is_tag_field_sortable(self, tag_field_name: str) -> bool:
        """Check if a tag field supports ordering (has a through model with position)."""
        return self._get_m2m_through_info(tag_field_name) is not None

    def get_tag_model_info(self, tag_field_name: str) -> dict | None:
        """Inspect the tag model and return metadata."""
        try:
            from django.db import models as dj_models
            field = self.model._meta.get_field(tag_field_name)
            if isinstance(field, dj_models.ManyToManyField):
                multiple = True
            elif isinstance(field, dj_models.ForeignKey):
                multiple = False
            else:
                return None
            tag_model = field.related_model

            # Find editable fields
            editable_fields = []
            title_field = None
            for f in tag_model._meta.get_fields():
                if isinstance(f, (dj_models.AutoField, dj_models.BigAutoField)):
                    continue
                if isinstance(f, (dj_models.ManyToOneRel, dj_models.ManyToManyRel, dj_models.ManyToManyField)):
                    continue
                if not hasattr(f, 'name'):
                    continue
                if hasattr(f, 'editable') and not f.editable:
                    continue
                if f.name in ('id', 'pk', 'created_at', 'updated_at'):
                    continue

                field_type = 'text'
                if isinstance(f, dj_models.TextField):
                    field_type = 'textarea'
                elif isinstance(f, (dj_models.IntegerField, dj_models.FloatField, dj_models.DecimalField)):
                    field_type = 'number'
                elif isinstance(f, dj_models.BooleanField):
                    field_type = 'checkbox'

                field_info = {
                    'name': f.name,
                    'label': f.verbose_name.title() if hasattr(f, 'verbose_name') else f.name.replace('_', ' ').title(),
                    'required': not getattr(f, 'blank', True),
                    'field_type': field_type,
                }
                editable_fields.append(field_info)

                # Auto-detect title field
                if not title_field and isinstance(f, dj_models.CharField):
                    title_field = f.name

            simple = len(editable_fields) == 1
            return {
                "model": tag_model,
                "simple": simple,
                "multiple": multiple,
                "title_field": title_field or (editable_fields[0]['name'] if editable_fields else None),
                "fields": editable_fields,
            }
        except Exception as e:
            print(f"[alive] Error getting tag model info: {e}")
            return None

    # Inline relation operations

    @async_db
    def get_inline_items(self, item_id: str, inline_info: dict) -> list[dict]:
        """Load related items for inline display on a parent item."""
        try:
            through_model = inline_info["through_model"]
            target_fk = inline_info["target_fk"]
            extra_field_names = inline_info.get("extra_field_names", [])

            # Build select_related list: target FK + any FK extra fields
            select_fields = [target_fk]
            for fname in extra_field_names:
                try:
                    f = through_model._meta.get_field(fname)
                    if isinstance(f, models.ForeignKey):
                        select_fields.append(fname)
                except Exception:
                    pass

            items = through_model.objects.filter(
                **{f"{inline_info['link_fk']}_id": int(item_id)}
            ).select_related(*select_fields)

            result = []
            for obj in items:
                target = getattr(obj, target_fk)
                item_data = {
                    "id": str(obj.pk),
                    "target_pk": str(target.pk),
                    "title": str(target),
                    "target_fields": {},
                    "through_fields": {},
                }
                # Collect target model fields
                target_cls = target.__class__
                if hasattr(target_cls, 'get_alive_conf'):
                    target_conf = target_cls.get_alive_conf()
                    if target_conf.fields:
                        for fname in target_conf.fields:
                            val = getattr(target, fname, "")
                            item_data["target_fields"][fname] = str(val) if val else ""

                # Collect through model extra fields
                for fname in extra_field_names:
                    val = getattr(obj, fname, "")
                    if hasattr(val, 'pk'):  # FK
                        item_data["through_fields"][fname] = str(val)
                        item_data["through_fields"][f"{fname}_pk"] = str(val.pk)
                    elif val is None:
                        item_data["through_fields"][fname] = ""
                        item_data["through_fields"][f"{fname}_pk"] = ""
                    else:
                        item_data["through_fields"][fname] = val

                result.append(item_data)
            return result
        except Exception as e:
            print(f"[alive] Error getting inline items: {e}")
            return []

    @async_db
    def get_through_item(self, inline_info: dict, through_pk: str):
        """Get a single through/join model instance by PK."""
        try:
            through_model = inline_info["through_model"]
            return through_model.objects.get(pk=int(through_pk))
        except (through_model.DoesNotExist, ValueError):
            return None

    @async_db
    def update_through_field(self, inline_info: dict, through_pk: str, field_name: str, value) -> bool:
        """Update a field on a through/join model instance."""
        try:
            through_model = inline_info["through_model"]
            obj = through_model.objects.get(pk=int(through_pk))
            setattr(obj, field_name, value)
            obj.save(update_fields=[field_name])
            return True
        except Exception as e:
            print(f"[alive] Error updating through field: {e}")
            return False

    @async_db
    def get_inline_target_field_value(self, inline_info: dict, target_pk: str, field_name: str):
        """Get a field value from an inline target model instance."""
        try:
            target_model = inline_info["target_model"]
            obj = target_model.objects.get(pk=int(target_pk))
            return getattr(obj, field_name, None)
        except Exception:
            return None

    @async_db
    def set_inline_target_field_value(self, inline_info: dict, target_pk: str, field_name: str, value) -> bool:
        """Set a field value on an inline target model instance."""
        try:
            target_model = inline_info["target_model"]
            obj = target_model.objects.get(pk=int(target_pk))
            setattr(obj, field_name, value)
            obj.save(update_fields=[field_name])
            return True
        except Exception as e:
            print(f"[alive] Error setting inline target field: {e}")
            return False

    @async_db
    def create_inline_item(
        self,
        inline_info: dict,
        parent_pk: str,
        target_values: dict[str, Any],
        extra_values: dict[str, Any],
    ) -> tuple | None:
        """Create a target item and a through/join model instance linking it to the parent."""
        try:
            target_model = inline_info["target_model"]
            through_model = inline_info["through_model"]

            # Create target (e.g., Card) with FK resolution
            resolved = {}
            for key, value in target_values.items():
                try:
                    field = target_model._meta.get_field(key)
                except Exception:
                    resolved[key] = value
                    continue
                if isinstance(field, models.ForeignKey):
                    resolved[f"{key}_id"] = int(value) if value else None
                else:
                    resolved[key] = value
            target = target_model(**resolved)
            target.full_clean()
            target.save()

            # Create through instance (e.g., CharacterCard)
            through_kwargs = {
                f"{inline_info['link_fk']}_id": int(parent_pk),
                f"{inline_info['target_fk']}_id": target.pk,
            }
            for key, value in extra_values.items():
                try:
                    field = through_model._meta.get_field(key)
                except Exception:
                    through_kwargs[key] = value
                    continue
                if isinstance(field, models.ForeignKey):
                    through_kwargs[f"{key}_id"] = int(value) if value else None
                else:
                    through_kwargs[key] = value
            through = through_model(**through_kwargs)
            through.full_clean()
            through.save()
            return (target, through)
        except Exception as e:
            print(f"[alive] Error creating inline item: {e}")
            return None

    @async_db
    def delete_through_item(self, inline_info: dict, through_pk: str) -> bool:
        """Delete a through/join model instance (unlink, not delete the target)."""
        try:
            through_model = inline_info["through_model"]
            through_model.objects.filter(pk=int(through_pk)).delete()
            return True
        except Exception as e:
            print(f"[alive] Error deleting through item: {e}")
            return False

    @async_db
    def get_fk_choices_for_model(self, model_label: str, field_name: str) -> list[tuple]:
        """Get FK choices for a field on any model (used for through model fields)."""
        try:
            from django.apps import apps
            target_model = apps.get_model(model_label)
            field = target_model._meta.get_field(field_name)
            if not hasattr(field, 'related_model'):
                return []
            related_model = field.related_model
            return [(obj.pk, str(obj)) for obj in related_model.objects.all()[:100]]
        except Exception as e:
            print(f"[alive] Error getting FK choices for model: {e}")
            return []

    def get_fk_field_info(self, field_name: str) -> dict | None:
        """Get metadata about a FK field."""
        try:
            from django.db import models as dj_models
            field = self.model._meta.get_field(field_name)
            if isinstance(field, dj_models.ForeignKey):
                return {
                    "name": field_name,
                    "label": field.verbose_name.title() if hasattr(field, 'verbose_name') else field_name.replace('_', ' ').title(),
                    "related_model": field.related_model,
                    "nullable": field.null,
                }
            return None
        except Exception:
            return None


# Registry of stores by model
_stores: dict[Type[models.Model], DjangoDataStore] = {}


def get_store(model: Type[models.Model]) -> DjangoDataStore:
    """Get or create a store for a model."""
    if model not in _stores:
        _stores[model] = DjangoDataStore(model)
    return _stores[model]
