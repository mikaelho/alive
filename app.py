"""Main entry point for the PyView cards application."""

import os
import sys

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Initialize Django BEFORE importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
import django
django.setup()

from pyview import PyView
from pyview.template import RootTemplateContext
from starlette.staticfiles import StaticFiles
from starlette.middleware.wsgi import WSGIMiddleware
from django.core.wsgi import get_wsgi_application
import uvicorn

# Import alive module
from alive import setup_alive, set_event_loop

# Keep the old manual view for comparison (can be removed later)
from views.cards.cards import CardsLiveView


def custom_root_template(context: RootTemplateContext) -> str:
    """Custom root template that loads hooks before app.js."""
    suffix = " | LiveView"
    title = context.get("title") or "Collaborative Cards"
    render_title = (title + suffix) if title else "LiveView"

    additional_head_elements = "\n".join(context["additional_head_elements"])

    main_content = f"""
      <div
        data-phx-main="true"
        data-phx-session="{context["session"]}"
        data-phx-static=""
        id="phx-{context["id"]}"
        >
        {context["content"]}
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
    <head>
      <title data-suffix="{suffix}">{render_title}</title>
      <meta name="csrf-token" content="{context["csrf_token"]}" />
      <meta charset="utf-8">
      <meta http-equiv="X-UA-Compatible" content="IE=edge">
      <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
      <link rel="stylesheet" href="/app-static/css/cards.css">
      <script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.2/Sortable.min.js"></script>
      <script src="/app-static/js/dragdrop.js"></script>
      <script src="/app-static/js/keyboard.js"></script>
      <script defer type="text/javascript" src="/static/assets/app.js"></script>
      {additional_head_elements}
    </head>
    <body>
      {main_content}
    </body>
</html>
"""


def create_app():
    """Create and configure the PyView application."""
    import asyncio
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app):
        # Store the event loop for signal handlers
        loop = asyncio.get_running_loop()
        set_event_loop(loop)
        yield

    app = PyView(lifespan=lifespan)

    # Use custom root template for hooks support
    app.rootTemplate = custom_root_template

    # Mount PyView's static assets
    app.mount("/static", StaticFiles(packages=[("pyview", "static")]), name="static")

    # Mount app's static assets (JS utilities, etc.)
    app.mount("/app-static", StaticFiles(directory="static"), name="app-static")

    # Mount Django static files for admin
    app.mount("/django-static", StaticFiles(directory="staticfiles"), name="django-static")

    # Mount Django admin via WSGI middleware
    django_wsgi_app = get_wsgi_application()
    app.mount("/admin", WSGIMiddleware(django_wsgi_app))

    # Setup Alive - auto-discovers models with AliveMixin and registers routes
    setup_alive(app, url_prefix="/alive")

    # Also keep the manual route at root for comparison
    app.add_live_view("/", CardsLiveView)

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
