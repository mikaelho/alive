"""Reusable UI components for Alive applications."""

from markupsafe import Markup


def render_theme_picker() -> str:
    """Render a theme picker dropdown for DaisyUI themes."""
    return '''
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
    '''


def render_theme_script(storage_key: str = "alive-theme") -> str:
    """Render the JavaScript for theme switching and persistence."""
    return f'''
    <script>
        function setTheme(theme) {{
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('{storage_key}', theme);
        }}
        (function() {{
            const saved = localStorage.getItem('{storage_key}');
            if (saved) {{
                document.documentElement.setAttribute('data-theme', saved);
            }}
        }})();
    </script>
    '''


def render_rating(value: int, name: str = "rating") -> str:
    """
    Render a rating component for values 1-10 using half-ball increments.

    Value 1 = 0.5 balls, Value 10 = 5 balls.
    5 balls with gaps between them, each ball can show half values.
    """
    if value < 1:
        value = 1
    if value > 10:
        value = 10

    # Build 5 balls, each with left and right halves
    balls = []

    for ball_num in range(5):
        left_pos = ball_num * 2 + 1   # 1, 3, 5, 7, 9
        right_pos = ball_num * 2 + 2  # 2, 4, 6, 8, 10

        # Color for this ball (gradient from secondary to primary)
        primary_pct = (ball_num / 4) * 100
        color_style = f"background: color-mix(in oklch, var(--color-primary) {primary_pct:.0f}%, var(--color-secondary));"

        # Left half
        if left_pos <= value:
            left_style = color_style
            left_class = ""
        else:
            left_style = ""
            left_class = "bg-base-300"

        # Right half
        if right_pos <= value:
            right_style = color_style
            right_class = ""
        else:
            right_style = ""
            right_class = "bg-base-300"

        # Each ball is two halves combined using clip-path
        balls.append(f'''
            <div class="relative w-3 h-3">
                <div class="absolute inset-0 rounded-full {left_class}" style="clip-path: inset(0 50% 0 0); {left_style}"></div>
                <div class="absolute inset-0 rounded-full {right_class}" style="clip-path: inset(0 0 0 50%); {right_style}"></div>
            </div>
        ''')

    return Markup(f'''
    <div class="flex gap-1 items-center">
        {"".join(balls)}
    </div>
    ''')
