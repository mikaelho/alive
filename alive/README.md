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

## Requirements

- Python 3.11+
- Django 4.2+
- PyView

## License

MIT
