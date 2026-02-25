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

import time as _time
from pathlib import Path

from .conf import AliveConf, TagFieldConf
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
from .ui import render_theme_picker, render_theme_script, render_rating

# Cache-busting token, set at import time so it changes on every server restart
CACHE_BUST = str(int(_time.time()))

# Global storage for registered models info (for drawer navigation)
_registered_models: list[dict] = []

# Frame context provider callback (set by app via setup_alive)
_frame_context_provider = None


def get_registered_models(player_id=None) -> list[dict]:
    """Get list of registered models for navigation, optionally filtered by player visibility."""
    if player_id is None:
        return _registered_models
    result = []
    for entry in _registered_models:
        model_cls = entry.get("_model")
        if model_cls:
            model_conf = model_cls.get_alive_conf()
            if model_conf.visible_to is not None and not model_conf.visible_to(player_id):
                continue
        result.append(entry)
    return result


def collect_static():
    """Run Django's collectstatic command."""
    from django.core.management import call_command
    call_command("collectstatic", "--noinput", verbosity=0)
    print("[alive] Static files collected")


def static_url(path: str) -> str:
    """Return a static URL with a cache-busting query parameter."""
    return f"{path}?v={CACHE_BUST}"


def setup_alive(app, url_prefix: str = "/alive", frame_context_provider=None):
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
        frame_context_provider: Async callable(session) -> dict providing frame data
    """
    global _registered_models, _frame_context_provider
    from django.apps import apps
    from pyview.vendor import ibis
    from pyview.vendor.ibis.loaders import FileReloader

    # Configure Ibis template loader for {% extends %} and {% include %}
    template_dir = str(Path(__file__).parent / "templates")
    ibis.loader = FileReloader(template_dir)

    # Store frame context provider for use by views
    _frame_context_provider = frame_context_provider

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
                "_model": model,
            })

            print(f"[alive] Registered {model._meta.label} at {path}")

    # Store globally for drawer navigation
    _registered_models = models_info

    # Register index page
    index_path = f"{url_prefix}/"
    index_view = create_index_liveview(models_info)
    app.add_live_view(index_path, index_view)
    print(f"[alive] Registered index at {index_path}")


__all__ = [
    "AliveConf",
    "TagFieldConf",
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
    "get_registered_models",
    "render_theme_picker",
    "render_theme_script",
    "render_rating",
    "collect_static",
    "static_url",
    "CACHE_BUST",
]
