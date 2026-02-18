"""Mixin for Django models to enable Alive functionality."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .conf import AliveConf, TagFieldConf


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
        if conf.create_fields:
            editable_fields = conf.create_fields
        elif conf.fields:
            editable_fields = conf.get_editable_fields()
        else:
            editable_fields = None

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
                field_type = 'fk'
                # Don't load choices here - will be loaded dynamically
                required = not field.blank

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

    @classmethod
    def get_fk_fields(cls) -> list[dict]:
        """
        Get FK fields with their metadata for the picker.

        Returns list of dicts with:
            - name: field name
            - label: human-readable label
            - related_model: the related model class
            - nullable: whether the field can be None
        """
        from django.db import models

        conf = cls.get_alive_conf()
        configured_fields = list(conf.fields) if conf.fields else None

        result = []
        for field in cls._meta.get_fields():
            if not isinstance(field, models.ForeignKey):
                continue
            if not hasattr(field, 'name'):
                continue

            # Skip if not in configured fields
            if configured_fields and field.name not in configured_fields:
                continue

            result.append({
                'name': field.name,
                'label': field.verbose_name.title() if hasattr(field, 'verbose_name') else field.name.replace('_', ' ').title(),
                'related_model': field.related_model,
                'nullable': field.null,
            })

        return result

    @classmethod
    def get_inline_info(cls) -> list[dict]:
        """
        Get info about inline relations for rendering related items on each item.

        For each relation in conf.inline, detects:
        - The through/join model (the model with FK back to this model)
        - The link FK (FK on through model pointing to this model)
        - The target FK (the other FK on through model, pointing to the model to create)
        - The target model

        Returns list of dicts with relation_name, through_model, link_fk,
        target_fk, target_model, label.
        """
        from django.db import models

        conf = cls.get_alive_conf()
        if not conf.inline:
            return []

        results = []
        for relation_name in conf.inline:
            try:
                field = cls._meta.get_field(relation_name)
            except Exception:
                continue

            # Expect a reverse FK relation (ManyToOneRel)
            if not isinstance(field, models.ManyToOneRel):
                continue

            through_model = field.related_model
            link_fk = field.field.name  # FK on through model pointing back to this model

            # Find the other FK on the through model (the target)
            target_fk = None
            target_model = None
            for f in through_model._meta.get_fields():
                if isinstance(f, models.ForeignKey) and f.name != link_fk:
                    target_fk = f.name
                    target_model = f.related_model
                    break

            if not target_fk or not target_model:
                continue

            # Compute extra field names (excluding link/target FKs and auto fields)
            exclude = {link_fk, target_fk, 'id', 'pk', 'created_at', 'updated_at'}
            extra_field_names = [
                f.name for f in through_model._meta.get_fields()
                if hasattr(f, 'name')
                and not isinstance(f, (models.ManyToOneRel, models.ManyToManyRel, models.ManyToManyField))
                and not isinstance(f, (models.AutoField, models.BigAutoField))
                and f.name not in exclude
            ]

            results.append({
                "relation_name": relation_name,
                "through_model": through_model,
                "link_fk": link_fk,
                "target_fk": target_fk,
                "target_model": target_model,
                "extra_field_names": extra_field_names,
                "label": relation_name.replace("_", " ").title(),
            })

        return results

    @classmethod
    def get_inline_extra_fields(cls, inline_info: dict) -> list[dict]:
        """
        Get creatable fields from a through/join model, excluding the two
        linking FKs and auto fields. Used for the inline create modal.
        """
        from django.db import models

        through_model = inline_info["through_model"]
        exclude = {inline_info["link_fk"], inline_info["target_fk"]}

        result = []
        for field in through_model._meta.get_fields():
            if isinstance(field, (models.ManyToOneRel, models.ManyToManyRel, models.ManyToManyField)):
                continue
            if isinstance(field, (models.AutoField, models.BigAutoField)):
                continue
            if not hasattr(field, 'name'):
                continue
            if hasattr(field, 'editable') and not field.editable:
                continue
            if field.name in ('created_at', 'updated_at', 'id', 'pk'):
                continue
            if field.name in exclude:
                continue

            required = not getattr(field, 'blank', True)
            field_type = 'text'
            choices = None
            default = ""

            if isinstance(field, models.TextField):
                field_type = 'textarea'
            elif isinstance(field, (models.IntegerField, models.FloatField, models.DecimalField,
                                    models.PositiveSmallIntegerField, models.PositiveIntegerField)):
                field_type = 'number'
                if hasattr(field, 'default') and field.default is not models.fields.NOT_PROVIDED:
                    default = str(field.default)
            elif isinstance(field, models.DateField):
                field_type = 'date'
            elif isinstance(field, models.DateTimeField):
                field_type = 'datetime'
            elif isinstance(field, models.BooleanField):
                field_type = 'checkbox'
            elif isinstance(field, models.ForeignKey):
                field_type = 'fk'
                required = not field.blank

            if hasattr(field, 'choices') and field.choices:
                field_type = 'select'
                choices = list(field.choices)

            result.append({
                'name': field.name,
                'label': field.verbose_name.title() if hasattr(field, 'verbose_name') else field.name.replace('_', ' ').title(),
                'required': required,
                'field_type': field_type,
                'choices': choices,
                'default': default,
            })

        return result

    @classmethod
    def get_tag_fields_conf(cls) -> list["TagFieldConf"]:
        """Get tag field configurations from AliveConf."""
        conf = cls.get_alive_conf()
        return list(conf.tag_fields)

    @classmethod
    def resolve_tag_scope(cls, tag_conf: "TagFieldConf") -> dict | None:
        """
        Resolve the scope for a tag field configuration.

        Walks the scope_path (e.g. "recipe" or "recipe__category") to find the
        scope model, then auto-detects the M2M field on the scope model that
        points to the tag model.

        Returns dict with scope_model, scope_m2m_field, scope_path_parts or None.
        """
        from django.db import models

        if not tag_conf.scope_path:
            return None

        # Find the tag model from the field (M2M or FK)
        try:
            tag_field = cls._meta.get_field(tag_conf.field_name)
        except Exception:
            return None

        if not isinstance(tag_field, (models.ManyToManyField, models.ForeignKey)):
            return None

        tag_model = tag_field.related_model

        # Walk the scope path to find the scope model
        parts = tag_conf.scope_path.split("__")
        current_model = cls
        for part in parts:
            try:
                field = current_model._meta.get_field(part)
            except Exception:
                return None
            if hasattr(field, 'related_model'):
                current_model = field.related_model
            else:
                return None

        scope_model = current_model

        # Find the M2M field on scope model that points to tag model
        scope_m2m_field = tag_conf.scope_m2m_field
        if not scope_m2m_field:
            for field in scope_model._meta.get_fields():
                if isinstance(field, models.ManyToManyField) and field.related_model == tag_model:
                    scope_m2m_field = field.name
                    break

        if not scope_m2m_field:
            return None

        return {
            "scope_model": scope_model,
            "scope_m2m_field": scope_m2m_field,
            "scope_path_parts": parts,
        }
