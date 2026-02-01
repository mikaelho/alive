"""Mixin for Django models to enable Alive functionality."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .conf import AliveConf


class AliveMixin:
    """
    Mixin for Django models that enables PyView live UI.

    Models using this mixin should define an 'alive' class attribute
    with an AliveConf instance specifying display/edit configuration.

    Example:
        class Task(models.Model, AliveMixin):
            alive = AliveConf(
                fields=("title", "description", "completed"),
                editable_fields=("title", "description"),
                title_field="title",
            )

            title = models.CharField(max_length=200)
            description = models.TextField(blank=True)
            completed = models.BooleanField(default=False)
    """

    alive: "AliveConf"

    @classmethod
    def get_alive_conf(cls) -> "AliveConf":
        """Get the AliveConf for this model, with defaults if not defined."""
        from .conf import AliveConf

        if hasattr(cls, 'alive') and isinstance(cls.alive, AliveConf):
            return cls.alive

        # Auto-generate config from model fields
        return cls._auto_generate_conf()

    @classmethod
    def _auto_generate_conf(cls) -> "AliveConf":
        """Auto-generate AliveConf from model field definitions."""
        from django.db import models
        from .conf import AliveConf

        fields = []
        for field in cls._meta.get_fields():
            # Skip relations and auto fields
            if isinstance(field, (models.ManyToOneRel, models.ManyToManyRel)):
                continue
            if isinstance(field, models.AutoField):
                continue
            if hasattr(field, 'name'):
                fields.append(field.name)

        return AliveConf(fields=tuple(fields))

    @classmethod
    def get_field_names(cls) -> list[str]:
        """Get all field names for this model."""
        conf = cls.get_alive_conf()
        if conf.fields:
            return list(conf.fields)
        return [f.name for f in cls._meta.get_fields() if hasattr(f, 'name')]
