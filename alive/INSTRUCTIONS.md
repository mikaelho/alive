# Alive - Real-time Django Model Views

Alive provides auto-generated real-time views for Django models using PyView.

## Quick Start

### 1. Add AliveMixin to your model

```python
from django.db import models
from alive import AliveMixin, AliveConf

class Recipe(models.Model, AliveMixin):
    alive = AliveConf(
        fields=("title", "description"),
        title_field="title",
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
```

### 2. Initialize Alive in your PyView app

```python
from pyview import PyView
from alive import setup_alive, set_event_loop

app = PyView()

# In your lifespan handler, store the event loop for signal broadcasting
@asynccontextmanager
async def lifespan(app):
    loop = asyncio.get_running_loop()
    set_event_loop(loop)
    yield

app = PyView(lifespan=lifespan)

# Register all models with AliveMixin
setup_alive(app, url_prefix="/alive")
```

### 3. Access your model views

Each model with `AliveMixin` gets a route at `/{url_prefix}/{model_name}/`:
- `/alive/recipe/`
- `/alive/ingredient/`

## AliveConf Options

```python
AliveConf(
    fields=("title", "content"),      # Fields to display
    editable_fields=("title",),       # Fields that can be edited (defaults to all fields)
    title_field="title",              # Field shown in card header
)
```

If `fields` is not specified, all model fields are auto-detected.

If `title_field` is not specified, it looks for common names: `name`, `title`, `label`.

## Features

- Real-time sync across all connected clients
- Edit locking prevents concurrent edits
- Django admin changes broadcast to PyView clients
- Drag-and-drop reordering (requires position field implementation)

## Requirements

- Django must be initialized before importing alive
- PyView app with WebSocket support
- Models must inherit from both `models.Model` and `AliveMixin`
