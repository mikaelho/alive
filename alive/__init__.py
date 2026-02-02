"""
Alive - Real-time Django model editing with PyView.

Provides a reactive frontend for Django models with:
- Real-time updates across all connected clients
- Edit locking to prevent conflicts
- Automatic signal-based sync when models change
- Configurable field display and editing

Usage:
    1. Add AliveMixin to your Django models:

        from alive import AliveMixin, AliveConf

        class Task(models.Model, AliveMixin):
            alive = AliveConf(
                fields=("title", "description", "completed"),
                editable_fields=("title", "description"),
            )
            title = models.CharField(max_length=200)
            ...

    2. Call setup_alive() in your app.py:

        from alive import setup_alive

        app = PyView(lifespan=lifespan)
        setup_alive(app)  # Auto-discovers models and registers routes
"""

from .conf import AliveConf
from .mixin import AliveMixin
from .store import DjangoDataStore, get_store
from .signals import setup_signals, set_event_loop
from .views import create_model_liveview, create_index_liveview
from .components import (
    EditableFieldMixin,
    ItemMixin,
    render_field_data,
    render_item_data,
)


def setup_alive(app, url_prefix: str = "/alive"):
    """
    Set up Alive for a PyView application.

    This function:
    1. Registers signal handlers for all models with AliveMixin
    2. Creates LiveViews for each model
    3. Registers routes at /{url_prefix}/{model_name}/
    4. Creates an index page at /{url_prefix}/

    Args:
        app: The PyView application instance
        url_prefix: URL prefix for alive routes (default: "/alive")
    """
    from django.apps import apps

    # Register signals
    setup_signals()

    # Collect model info for index page
    models_info = []

    # Find all models with AliveMixin and register routes
    for model in apps.get_models():
        if issubclass(model, AliveMixin):
            # Create LiveView for this model
            view_class = create_model_liveview(model, url_prefix)

            # Register route
            model_name = model._meta.model_name
            path = f"{url_prefix}/{model_name}/"
            app.add_live_view(path, view_class)

            # Collect info for index page
            models_info.append({
                "title": model._meta.verbose_name_plural.title(),
                "description": f"Manage {model._meta.verbose_name_plural}",
                "url": path,
            })

            print(f"[alive] Registered {model._meta.label} at {path}")

    # Register index page
    index_path = f"{url_prefix}/"
    index_view = create_index_liveview(models_info)
    app.add_live_view(index_path, index_view)
    print(f"[alive] Registered index at {index_path}")


__all__ = [
    "AliveConf",
    "AliveMixin",
    "DjangoDataStore",
    "get_store",
    "setup_alive",
    "setup_signals",
    "set_event_loop",
    "create_model_liveview",
    "create_index_liveview",
    "EditableFieldMixin",
    "ItemMixin",
    "render_field_data",
    "render_item_data",
]
