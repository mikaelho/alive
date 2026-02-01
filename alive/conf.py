"""Configuration classes for Alive models."""

from dataclasses import dataclass, field
from typing import Sequence


@dataclass
class AliveConf:
    """
    Configuration for how a Django model should be displayed/edited in PyView.

    Attributes:
        fields: Fields to display (default: auto-detect from model)
        editable_fields: Fields that can be edited (default: same as fields, minus id/pk)
        title_field: Field to use as the card/row title (default: 'name' or 'title' or first CharField)
        list_fields: Fields to show in list/table view (default: same as fields)
    """

    fields: Sequence[str] = ()
    editable_fields: Sequence[str] | None = None
    title_field: str | None = None
    list_fields: Sequence[str] | None = None

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
