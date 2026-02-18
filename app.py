"""Main entry point for the PyView application with Alive module."""

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
from alive import (
    setup_alive,
    set_event_loop,
    get_registered_models,
    render_theme_picker,
    render_theme_script,
    render_rating,
    collect_static,
    static_url,
)


def custom_root_template(context: RootTemplateContext) -> str:
    """Custom root template that loads hooks before app.js."""
    suffix = " | LiveView"
    title = context.get("title") or "Alive"
    render_title = (title + suffix) if title else "LiveView"

    additional_head_elements = "\n".join(context["additional_head_elements"])

    # Build sidebar menu from registered models
    models = get_registered_models()
    sidebar_items = "\n".join([
        f'<li><a href="{m["url"]}">{m["title"]}</a></li>'
        for m in models
    ])

    main_content = f"""
      <div
        data-phx-main="true"
        data-phx-session="{context["session"]}"
        data-phx-static=""
        id="phx-{context["id"]}"
        >
        {context["content"]}
    </div>"""

    navbar = f"""
      <div class="navbar bg-base-100 shadow mb-4">
        <div class="flex-1">
          <label for="alive-drawer" class="btn btn-ghost lg:hidden">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </label>
          <a href="/alive/" class="btn btn-ghost text-xl">Alive</a>
        </div>
        <div class="flex-none">
          {render_theme_picker()}
        </div>
      </div>
    """

    theme_script = render_theme_script()

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
    <head>
      <title data-suffix="{suffix}">{render_title}</title>
      <meta name="csrf-token" content="{context["csrf_token"]}" />
      <meta charset="utf-8">
      <meta http-equiv="X-UA-Compatible" content="IE=edge">
      <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
      <link href="https://cdn.jsdelivr.net/npm/daisyui@5" rel="stylesheet" type="text/css" />
      <link href="https://cdn.jsdelivr.net/npm/daisyui@5/themes.css" rel="stylesheet" type="text/css" />
      <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
      <link rel="stylesheet" href="{static_url('/django-static/alive/css/alive.css')}">
      <script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.2/Sortable.min.js"></script>
      <script src="{static_url('/django-static/alive/js/dragdrop.js')}"></script>
      <script src="{static_url('/django-static/alive/js/keyboard.js')}"></script>
      <script defer type="text/javascript" src="/static/assets/app.js"></script>
      {additional_head_elements}
    </head>
    <body class="bg-base-200 min-h-screen">
      <div class="drawer lg:drawer-open">
        <input id="alive-drawer" type="checkbox" class="drawer-toggle" />
        <div class="drawer-content">
          {navbar}
          {main_content}
        </div>
        <div class="drawer-side">
          <label for="alive-drawer" aria-label="close sidebar" class="drawer-overlay"></label>
          <div class="bg-base-100 min-h-full w-64 p-4 flex flex-col">
            <ul class="menu flex-1">
              <li class="menu-title">Models</li>
              {sidebar_items}
            </ul>
            <div class="border-t border-base-300 pt-4 mt-4">
              <div class="text-xs text-base-content/50 mb-2">Rating Examples</div>
              <div class="space-y-2">
                <div class="flex items-center justify-between">
                  <span class="text-sm">1:</span>
                  {render_rating(1, "demo-1")}
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-sm">3:</span>
                  {render_rating(3, "demo-3")}
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-sm">7:</span>
                  {render_rating(7, "demo-7")}
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-sm">10:</span>
                  {render_rating(10, "demo-10")}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      {theme_script}
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

    # Collect static files before mounting
    collect_static()

    # Mount PyView's static assets
    app.mount("/static", StaticFiles(packages=[("pyview", "static")]), name="static")

    # Mount Django static files (includes alive module assets)
    app.mount("/django-static", StaticFiles(directory="staticfiles"), name="django-static")

    # Mount Django admin via WSGI middleware
    django_wsgi_app = get_wsgi_application()
    app.mount("/admin", WSGIMiddleware(django_wsgi_app))

    # Setup Alive - auto-discovers models with AliveMixin and registers routes
    setup_alive(app, url_prefix="/alive")

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
