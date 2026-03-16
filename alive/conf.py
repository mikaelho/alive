"""Configuration classes for Alive models."""

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence


@dataclass
class TagFieldConf:
    """Configuration for a tag-like M2M field."""
    field_name: str                    # M2M field on this model (e.g., "tags")
    scope_path: str | None = None      # Path to scope object (e.g., "recipe" or "recipe__category")
    scope_m2m_field: str | None = None # M2M field on scope pointing to tag model (auto-detected if None)
    label: str | None = None           # Display label (defaults to field_name.title())


@dataclass
class AliveConf:
    """
    Configuration for how a Django model should be displayed/edited in PyView.

    Attributes:
        fields: Fields to display (default: auto-detect from model)
        editable_fields: Fields that can be edited (default: same as fields, minus id/pk)
        title_field: Field to use as the card/row title (default: 'name' or 'title' or first CharField)
        list_fields: Fields to show in list/table view (default: same as fields)
        dive_to: Relation field names to show "dive" buttons for (navigates to related objects)
    """

    fields: Sequence[str] = ()
    editable_fields: Sequence[str] | None = None
    create_fields: Sequence[str] | None = None
    title_field: str | None = None
    list_fields: Sequence[str] | None = None
    dive_to: Sequence[str] = ()
    tag_fields: Sequence["TagFieldConf"] = ()
    compact_fields: Sequence[str] = ()
    inline: Sequence[str] = ()
    template: str | None = None
    visible_to: Callable[[Any], bool] | None = None
    filter_queryset: Callable[[Any, Any], Any] | None = None
    # Extension hooks for app-specific behavior
    event_handler: Callable | None = None        # async (event, payload, socket) -> bool
    mount_hook: Callable | None = None           # async (socket, session) -> None
    params_hook: Callable | None = None          # async (socket, url, params) -> None
    refresh_hook: Callable | None = None         # async (socket) -> None
    info_hook: Callable | None = None            # async (event, socket) -> None
    disconnect_hook: Callable | None = None      # async (socket) -> None
    extra_subscriptions: Callable | None = None  # async (socket) -> list[str]
    post_create_hook: Callable | None = None     # async (socket, item) -> None
    context_class: type | None = None            # Subclass of ModelContext with extra fields

    def get_editable_fields(self) -> Sequence[str]:
        """Get editable fields, defaulting to fields minus common non-editable ones."""
        if self.editable_fields is not None:
            return self.editable_fields
        # Default: all fields except id, pk, created_at, updated_at
        non_editable = {'id', 'pk', 'created_at', 'updated_at'}
        return [f for f in self.fields if f not in non_editable]

    def get_title_field(self, model_fields: Sequence[str]) -> str | None:
        """Get the title field, with smart defaults."""
        if self.title_field:
            return self.title_field
        # Try common title field names
        for candidate in ('name', 'title', 'label', 'subject'):
            if candidate in model_fields:
                return candidate
        # Fall back to first field
        return model_fields[0] if model_fields else None
