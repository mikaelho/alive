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
from alive import setup_alive, set_event_loop, get_registered_models


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

    navbar = """
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
          <div class="dropdown dropdown-end">
            <div tabindex="0" role="button" class="btn btn-ghost">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
              </svg>
              <span class="hidden sm:inline">Theme</span>
            </div>
            <div tabindex="-1" class="dropdown-content bg-base-100 rounded-box w-52 z-1 shadow-sm" style="max-height: 70vh; overflow-y: auto;">
              <ul class="menu p-2">
              <li class="menu-title"><span>Light</span></li>
              <li><a onclick="setTheme('light')">Light</a></li>
              <li><a onclick="setTheme('cupcake')">Cupcake</a></li>
              <li><a onclick="setTheme('bumblebee')">Bumblebee</a></li>
              <li><a onclick="setTheme('emerald')">Emerald</a></li>
              <li><a onclick="setTheme('corporate')">Corporate</a></li>
              <li><a onclick="setTheme('retro')">Retro</a></li>
              <li><a onclick="setTheme('valentine')">Valentine</a></li>
              <li><a onclick="setTheme('garden')">Garden</a></li>
              <li><a onclick="setTheme('lofi')">Lo-Fi</a></li>
              <li><a onclick="setTheme('pastel')">Pastel</a></li>
              <li><a onclick="setTheme('fantasy')">Fantasy</a></li>
              <li><a onclick="setTheme('wireframe')">Wireframe</a></li>
              <li><a onclick="setTheme('cmyk')">CMYK</a></li>
              <li><a onclick="setTheme('autumn')">Autumn</a></li>
              <li><a onclick="setTheme('acid')">Acid</a></li>
              <li><a onclick="setTheme('lemonade')">Lemonade</a></li>
              <li><a onclick="setTheme('winter')">Winter</a></li>
              <li><a onclick="setTheme('nord')">Nord</a></li>
              <li><a onclick="setTheme('caramellatte')">Caramellatte</a></li>
              <li><a onclick="setTheme('silk')">Silk</a></li>
              <li class="menu-title"><span>Dark</span></li>
              <li><a onclick="setTheme('dark')">Dark</a></li>
              <li><a onclick="setTheme('synthwave')">Synthwave</a></li>
              <li><a onclick="setTheme('cyberpunk')">Cyberpunk</a></li>
              <li><a onclick="setTheme('halloween')">Halloween</a></li>
              <li><a onclick="setTheme('forest')">Forest</a></li>
              <li><a onclick="setTheme('aqua')">Aqua</a></li>
              <li><a onclick="setTheme('luxury')">Luxury</a></li>
              <li><a onclick="setTheme('dracula')">Dracula</a></li>
              <li><a onclick="setTheme('business')">Business</a></li>
              <li><a onclick="setTheme('night')">Night</a></li>
              <li><a onclick="setTheme('coffee')">Coffee</a></li>
              <li><a onclick="setTheme('dim')">Dim</a></li>
              <li><a onclick="setTheme('sunset')">Sunset</a></li>
              <li><a onclick="setTheme('abyss')">Abyss</a></li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    """

    theme_script = """
      <script>
        function setTheme(theme) {
          document.documentElement.setAttribute('data-theme', theme);
          localStorage.setItem('alive-theme', theme);
        }
        // Load saved theme on page load
        (function() {
          const saved = localStorage.getItem('alive-theme');
          if (saved) {
            document.documentElement.setAttribute('data-theme', saved);
          }
        })();
      </script>
    """

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
      <link rel="stylesheet" href="/django-static/alive/css/alive.css">
      <script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.2/Sortable.min.js"></script>
      <script src="/django-static/alive/js/dragdrop.js"></script>
      <script src="/django-static/alive/js/keyboard.js"></script>
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
          <ul class="menu bg-base-100 min-h-full w-64 p-4">
            <li class="menu-title">Models</li>
            {sidebar_items}
          </ul>
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
