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

    @classmethod
    def get_creatable_fields(cls) -> list[dict]:
        """
        Get fields that should be shown in the creation form.

        Returns list of dicts with:
            - name: field name
            - label: human-readable label
            - required: whether the field is required
            - field_type: 'text', 'textarea', 'number', 'date', 'choice', etc.
            - choices: list of (value, label) tuples for choice fields
        """
        from django.db import models

        conf = cls.get_alive_conf()
        editable_fields = conf.get_editable_fields() if conf.fields else None

        result = []
        for field in cls._meta.get_fields():
            # Skip relations, auto fields, and non-editable fields
            if isinstance(field, (models.ManyToOneRel, models.ManyToManyRel, models.ManyToManyField)):
                continue
            if isinstance(field, (models.AutoField, models.BigAutoField)):
                continue
            if not hasattr(field, 'name'):
                continue
            if hasattr(field, 'editable') and not field.editable:
                continue

            # Skip fields not in editable_fields if specified
            if editable_fields and field.name not in editable_fields:
                continue

            # Skip auto-managed fields
            if field.name in ('created_at', 'updated_at', 'id', 'pk'):
                continue

            # Determine if required
            required = not getattr(field, 'blank', True)

            # Determine field type
            field_type = 'text'
            choices = None

            if isinstance(field, models.TextField):
                field_type = 'textarea'
            elif isinstance(field, (models.IntegerField, models.FloatField, models.DecimalField)):
                field_type = 'number'
            elif isinstance(field, models.DateField):
                field_type = 'date'
            elif isinstance(field, models.DateTimeField):
                field_type = 'datetime'
            elif isinstance(field, models.BooleanField):
                field_type = 'checkbox'
            elif isinstance(field, models.ForeignKey):
                field_type = 'select'
                # Get choices from related model
                related_model = field.related_model
                choices = [(obj.pk, str(obj)) for obj in related_model.objects.all()[:100]]
                required = not field.null

            # Check for choices on the field
            if hasattr(field, 'choices') and field.choices:
                field_type = 'select'
                choices = list(field.choices)

            result.append({
                'name': field.name,
                'label': field.verbose_name.title() if hasattr(field, 'verbose_name') else field.name.replace('_', ' ').title(),
                'required': required,
                'field_type': field_type,
                'choices': choices,
            })

        return result

    @classmethod
    def get_dive_relations(cls, url_prefix: str = "/alive") -> list[dict]:
        """
        Get info about dive-to relations for building navigation buttons.

        Returns a list of dicts with:
            - name: the relation field name
            - label: human-readable label for the button
            - target_model: the related model class
            - target_url: base URL for the target model's view
            - filter_param: query parameter name to filter by this model
        """
        from django.db import models

        conf = cls.get_alive_conf()
        if not conf.dive_to:
            return []

        relations = []
        for field_name in conf.dive_to:
            try:
                field = cls._meta.get_field(field_name)
            except Exception:
                continue

            # Determine target model and filter param based on relation type
            target_model = None
            filter_param = None

            if isinstance(field, models.ManyToManyField):
                target_model = field.related_model
                # Filter param is the reverse accessor name on target model
                filter_param = field.related_query_name() or cls._meta.model_name

            elif isinstance(field, models.ForeignKey):
                target_model = field.related_model
                # For FK, we link to the single related object (not a filtered list)
                filter_param = None

            elif isinstance(field, (models.ManyToOneRel, models.ManyToManyRel)):
                # Reverse relation - e.g., recipe.meals (from Meal.recipe FK)
                target_model = field.related_model
                # Filter on the FK field name
                filter_param = field.field.name

            if target_model and hasattr(target_model, 'alive'):
                target_model_name = target_model._meta.model_name
                relations.append({
                    "name": field_name,
                    "label": field_name.replace("_", " ").title(),
                    "target_model": target_model,
                    "target_url": f"{url_prefix}/{target_model_name}/",
                    "filter_param": filter_param,
                })

        return relations
