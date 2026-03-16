# Alive

Real-time Django model views with PyView.

**Status: Alpha** - API may change.

## Installation

```bash
pip install alive
```

## Quick Start

### 1. Add AliveMixin to your model

```python
from django.db import models
from alive import AliveMixin, AliveConf

class Recipe(models.Model, AliveMixin):
    alive = AliveConf(
        fields=("title", "description"),
        title_field="title",
        dive_to=("ingredients",),  # Navigate to related objects
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    ingredients = models.ManyToManyField("Ingredient")
```

### 2. Initialize Alive in your PyView app

```python
import asyncio
from contextlib import asynccontextmanager
from pyview import PyView
from alive import setup_alive, set_event_loop

@asynccontextmanager
async def lifespan(app):
    loop = asyncio.get_running_loop()
    set_event_loop(loop)
    yield

app = PyView(lifespan=lifespan)
setup_alive(app, url_prefix="/alive")
```

### 3. Add 'alive' to INSTALLED_APPS

```python
INSTALLED_APPS = [
    ...
    'alive',
]
```

### 4. Collect static files

```bash
python manage.py collectstatic
```

## Features

- Real-time sync across all connected clients
- Edit locking prevents concurrent edits
- Create new items with automatic relationship linking
- Navigate between related models with "dive" buttons
- Django admin changes broadcast to PyView clients
- Keyboard shortcuts (Cmd+Enter to save, Esc to cancel)

## AliveConf Options

```python
AliveConf(
    fields=("title", "content"),      # Fields to display
    editable_fields=("title",),       # Editable fields (default: all)
    title_field="title",              # Card header field
    dive_to=("ingredients",),         # Related models to show dive buttons
)
```

## Extension Hooks

Alive is a **generic** CRUD framework. App-specific behavior belongs in the consuming application, not in alive. Use hooks on `AliveConf` to extend behavior:

```python
AliveConf(
    fields=("name",),
    event_handler=my_event_handler,        # async (event, payload, socket) -> bool
    mount_hook=my_mount_hook,              # async (socket, session) -> None
    params_hook=my_params_hook,            # async (socket, url, params) -> None
    refresh_hook=my_refresh_hook,          # async (socket) -> None
    info_hook=my_info_hook,               # async (event, socket) -> None
    disconnect_hook=my_disconnect_hook,    # async (socket) -> None
    extra_subscriptions=my_subscriptions,  # async (socket) -> list[str]
    post_create_hook=my_post_create,      # async (socket, item) -> None
)
```

Hooks can set dynamic attributes on `socket.context` — these are automatically included in template variables alongside declared dataclass fields.

### Custom Templates

Pass `template_dirs` to `setup_alive()` to override alive's default templates:

```python
setup_alive(app, url_prefix="/alive", template_dirs=["/path/to/app/templates"])
```

App template directories are searched before alive's defaults, so you can override `frame_top.html`, `frame_bottom.html`, or provide custom model templates.

## Requirements

- Python 3.11+
- Django 4.2+
- PyView

## License

MIT
