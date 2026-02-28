"""Reusable UI components for Alive applications."""

import math
import re

from markupsafe import Markup


def render_theme_picker() -> Markup:
    """Render a theme picker dropdown for DaisyUI themes."""
    return Markup('''
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
    ''')


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


_DIE_PIPS = {
    1: [(20, 20)],
    2: [(29, 11), (11, 29)],
    3: [(29, 11), (20, 20), (11, 29)],
    4: [(11, 11), (29, 11), (11, 29), (29, 29)],
    5: [(11, 11), (29, 11), (20, 20), (11, 29), (29, 29)],
    6: [(11, 11), (29, 11), (11, 20), (29, 20), (11, 29), (29, 29)],
}


def render_die_svg(value: int, css_class: str = "h-8 w-8", dashed: bool = False) -> Markup:
    """Render an SVG d6 face with pips. Theme-sensitive via CSS classes."""
    if dashed:
        body = (
            '<rect x="2" y="2" width="36" height="36" rx="5" '
            'fill="none" stroke="currentColor" stroke-width="1.5" stroke-dasharray="4 2" opacity="0.4"/>'
        )
        pips = ""
    else:
        body = '<rect x="2" y="2" width="36" height="36" rx="5" class="die-face"/>'
        pips = "".join(
            f'<circle cx="{x}" cy="{y}" r="3.5" class="die-pip"/>'
            for x, y in _DIE_PIPS.get(value, [])
        )
    return Markup(
        f'<svg viewBox="0 0 40 40" class="{css_class}" xmlns="http://www.w3.org/2000/svg">'
        f'{body}{pips}</svg>'
    )


DIE_CSS = Markup('''<style>
    .die-face { fill: var(--color-base-content); }
    .die-pip { fill: var(--color-base-100); }
    .die-primary .die-face { fill: var(--color-primary); }
    .die-primary .die-pip { fill: var(--color-primary-content); }
    .die-faded { opacity: 0.3; }
</style>''')


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


# --- Hex map rendering ---

_SQRT3 = math.sqrt(3)

HEX_SYMBOL_LABELS = {
    "grass": "Grass",
    "hills": "Hills",
    "mushroom": "Mushrooms",
    "lake": "Lake",
    "swamp": "Swamp",
    "spikes": "Spikes",
    "cliff": "Cliff",
    "vertical_caves": "Vertical Caves",
    "fungal_forest": "Fungal Forest",
    "crystal_pillars": "Crystal Pillars",
    "geysers": "Geysers",
    "bones": "Bones",
    "floating_rocks": "Floating Rocks",
    "cavern_city": "Cavern City",
    "tower": "Tower",
    "fortress": "Fortress",
    "castle": "Castle",
}

HEX_OVERLAY_LABELS = {
    "ruins": "Ruins",
    "dwellings": "Dwellings",
    "monument": "Monument",
    "hazard": "Hazard",
    "curse": "Curse",
    "sanctum": "Sanctum",
    "myth": "Myth",
}

_HEX_SYMBOLS = {
    # Subtle grass tufts — very unobtrusive
    "grass": '''<symbol id="sym-grass" viewBox="-12 -12 24 24">
        <path d="M-7,6 Q-7,4 -8,2" stroke-width="1" fill="none" class="hex-symbol-stroke" opacity="0.5"/>
        <path d="M-6,6 Q-5,4 -4,3" stroke-width="1" fill="none" class="hex-symbol-stroke" opacity="0.5"/>
        <path d="M-2,6 Q-2,3 -4,1" stroke-width="1" fill="none" class="hex-symbol-stroke" opacity="0.5"/>
        <path d="M-1,6 Q0,4 1,3" stroke-width="1" fill="none" class="hex-symbol-stroke" opacity="0.5"/>
        <path d="M0,6 Q1,4 3,2" stroke-width="1" fill="none" class="hex-symbol-stroke" opacity="0.5"/>
        <path d="M5,6 Q5,4 4,3" stroke-width="1" fill="none" class="hex-symbol-stroke" opacity="0.5"/>
        <path d="M6,6 Q6,3 8,2" stroke-width="1" fill="none" class="hex-symbol-stroke" opacity="0.5"/>
    </symbol>''',
    # Low rolling hills — gentle rounded bumps
    "hills": '''<symbol id="sym-hills" viewBox="-12 -12 24 24">
        <path d="M-10,5 Q-7,0 -4,5" stroke-width="1.5" fill="none" class="hex-symbol-stroke"/>
        <path d="M-6,5 Q-2,-1 2,5" stroke-width="1.5" fill="none" class="hex-symbol-stroke"/>
        <path d="M0,5 Q4,1 8,5" stroke-width="1.5" fill="none" class="hex-symbol-stroke"/>
    </symbol>''',
    # Three small mushrooms of different sizes
    "mushroom": '''<symbol id="sym-mushroom" viewBox="-12 -12 24 24">
        <rect x="-7" y="4" width="2.5" height="3" rx="0.8" class="hex-symbol"/>
        <path d="M-9,4 C-9,2.5 -7.5,0.5 -5.5,0.5 C-3.5,2.5 -2.5,2.5 -2.5,4 Z" class="hex-symbol"/>
        <circle cx="-6" cy="2" r="0.7" class="hex-spot"/>
        <rect x="-1.5" y="2" width="3" height="4.5" rx="1" class="hex-symbol"/>
        <path d="M-4,2 C-4,0 -2.5,-2 0.5,-2 C3.5,0 4,0 4,2 Z" class="hex-symbol"/>
        <circle cx="-1" cy="0" r="0.8" class="hex-spot"/>
        <circle cx="1.5" cy="-1" r="0.6" class="hex-spot"/>
        <rect x="5" y="4.5" width="2" height="2.5" rx="0.6" class="hex-symbol"/>
        <path d="M4,4.5 C4,3.5 4.8,2 6.2,2 C7.6,3.5 8,3.5 8,4.5 Z" class="hex-symbol"/>
        <circle cx="5.8" cy="3" r="0.5" class="hex-spot"/>
    </symbol>''',
    # Wavy water surface
    "lake": '''<symbol id="sym-lake" viewBox="-12 -12 24 24">
        <path d="M-8,-3 Q-5,-6 -2,-3 Q1,-6 4,-3 Q7,-6 8,-3" stroke-width="1.4" fill="none" class="hex-symbol-stroke"/>
        <path d="M-8,1 Q-5,-2 -2,1 Q1,-2 4,1 Q7,-2 8,1" stroke-width="1.4" fill="none" class="hex-symbol-stroke"/>
        <path d="M-8,5 Q-5,2 -2,5 Q1,2 4,5 Q7,2 8,5" stroke-width="1.4" fill="none" class="hex-symbol-stroke"/>
    </symbol>''',
    # Swamp — water ripples with reeds poking up
    "swamp": '''<symbol id="sym-swamp" viewBox="-12 -12 24 24">
        <path d="M-10,2 Q-7,-1 -4,2 Q-1,-1 2,2 Q5,-1 8,2" stroke-width="1.5" fill="none" class="hex-symbol-stroke"/>
        <path d="M-8,6 Q-5,3 -2,6 Q1,3 4,6 Q7,3 9,6" stroke-width="1.5" fill="none" class="hex-symbol-stroke"/>
        <line x1="-7" y1="2" x2="-7" y2="-5" stroke-width="1.2" class="hex-symbol-stroke"/>
        <line x1="-7" y1="-5" x2="-8.5" y2="-7" stroke-width="1" class="hex-symbol-stroke"/>
        <line x1="-7" y1="-5" x2="-5.5" y2="-7.5" stroke-width="1" class="hex-symbol-stroke"/>
        <line x1="1" y1="2" x2="1" y2="-6" stroke-width="1.2" class="hex-symbol-stroke"/>
        <line x1="1" y1="-6" x2="-0.5" y2="-8" stroke-width="1" class="hex-symbol-stroke"/>
        <line x1="1" y1="-6" x2="2.5" y2="-8.5" stroke-width="1" class="hex-symbol-stroke"/>
        <line x1="7" y1="2" x2="7" y2="-3" stroke-width="1.2" class="hex-symbol-stroke"/>
        <line x1="7" y1="-3" x2="5.8" y2="-5" stroke-width="1" class="hex-symbol-stroke"/>
        <line x1="7" y1="-3" x2="8.2" y2="-5" stroke-width="1" class="hex-symbol-stroke"/>
    </symbol>''',
    # Straight spikes — stalactites down and stalagmites up, symmetric
    "spikes": '''<symbol id="sym-spikes" viewBox="-12 -12 24 24">
        <path d="M-8,-10 L-7,0 L-6,-10 Z" class="hex-symbol"/>
        <path d="M-2,-10 L-1,2 L0,-10 Z" class="hex-symbol"/>
        <path d="M5,-10 L6,-3 L7,-10 Z" class="hex-symbol"/>
        <path d="M-5,10 L-4,3 L-3,10 Z" class="hex-symbol"/>
        <path d="M1,10 L2,1 L3,10 Z" class="hex-symbol"/>
        <path d="M7,10 L8,5 L9,10 Z" class="hex-symbol"/>
    </symbol>''',
    # Sheer cliff drop — jagged top edge with vertical lines down from corners
    "cliff": '''<symbol id="sym-cliff" viewBox="-12 -12 24 24">
        <path d="M-10,-2 L-7,-4 L-4,-1 L-1,-5 L2,-2 L5,-4 L8,-1 L10,-3" stroke-width="2" fill="none" class="hex-symbol-stroke"/>
        <line x1="-7" y1="-4" x2="-7" y2="7" stroke-width="1" class="hex-symbol-stroke"/>
        <line x1="-1" y1="-5" x2="-1" y2="7" stroke-width="1" class="hex-symbol-stroke"/>
        <line x1="5" y1="-4" x2="5" y2="7" stroke-width="1" class="hex-symbol-stroke"/>
        <line x1="10" y1="-3" x2="10" y2="5" stroke-width="1" class="hex-symbol-stroke"/>
        <line x1="-10" y1="-2" x2="-10" y2="6" stroke-width="1" class="hex-symbol-stroke"/>
    </symbol>''',
    # Cave passage meandering through rock — flat-top hex
    "vertical_caves": '''<symbol id="sym-vertical_caves" viewBox="-12 -12 24 24">
        <polygon points="-5,-9 5,-9 10,0 5,9 -5,9 -10,0" class="hex-symbol"/>
        <path d="M-7,9 Q-5,6 -4,2 Q-3,-1 -1,-3 Q1,-5 2,-4 Q3,-3 4,-1 Q5,1 7,-2 Q8,-5 8,-8
                 L10,-8 Q10,-5 9,-2 Q8,1 7,0 Q6,-1 4,-3 Q3,-5 2,-6 Q1,-7 -1,-5 Q-3,-3 -4,0 Q-5,4 -5,9 Z" class="hex-spot"/>
    </symbol>''',
    # Dense fungal trees
    "fungal_forest": '''<symbol id="sym-fungal_forest" viewBox="-12 -12 24 24">
        <rect x="-8" y="2" width="1.5" height="5" rx="0.5" class="hex-symbol"/>
        <ellipse cx="-7.2" cy="1" rx="3.5" ry="2.5" class="hex-symbol"/>
        <rect x="-3" y="-1" width="2" height="7" rx="0.7" class="hex-symbol"/>
        <ellipse cx="-2" cy="-2.5" rx="4.5" ry="3" class="hex-symbol"/>
        <rect x="3" y="1" width="1.5" height="5.5" rx="0.5" class="hex-symbol"/>
        <ellipse cx="3.8" cy="0" rx="3.5" ry="2.5" class="hex-symbol"/>
        <rect x="7" y="3" width="1.2" height="4" rx="0.4" class="hex-symbol"/>
        <ellipse cx="7.5" cy="2" rx="2.5" ry="1.8" class="hex-symbol"/>
    </symbol>''',
    # Tall crystal pillars
    "crystal_pillars": '''<symbol id="sym-crystal_pillars" viewBox="-12 -12 24 24">
        <polygon points="-7,7 -8,-3 -6,-7 -4,-3" class="hex-symbol"/>
        <polygon points="-2,7 -3,-1 -1,-6 1,-1" class="hex-symbol"/>
        <polygon points="3,7 2,0 4,-5 6,0" class="hex-symbol"/>
        <polygon points="7,7 6,2 8,-2 9,2" class="hex-symbol"/>
    </symbol>''',
    # Steam vents / geysers
    "geysers": '''<symbol id="sym-geysers" viewBox="-12 -12 24 24">
        <ellipse cx="0" cy="5" rx="4" ry="2" class="hex-symbol"/>
        <path d="M-1,3 Q-3,-1 -1,-4 Q0,-6 1,-4 Q3,-1 1,3" class="hex-symbol" opacity="0.08"/>
        <path d="M-0.5,3 Q-2,0 -0.5,-3 Q0,-5 0.5,-3 Q2,0 0.5,3" class="hex-symbol" opacity="0.06"/>
        <circle cx="-1.5" cy="-2" r="1" class="hex-symbol" opacity="0.06"/>
        <circle cx="1" cy="-5" r="0.8" class="hex-symbol" opacity="0.06"/>
        <circle cx="0" cy="-7" r="0.6" class="hex-symbol" opacity="0.05"/>
    </symbol>''',
    # Skull and bones
    "bones": '''<symbol id="sym-bones" viewBox="-12 -12 24 24">
        <circle cx="0" cy="-3" r="3.5" class="hex-symbol"/>
        <circle cx="-1.5" cy="-4" r="0.8" class="hex-spot"/>
        <circle cx="1.5" cy="-4" r="0.8" class="hex-spot"/>
        <path d="M-1,-1.5 L1,-1.5" stroke-width="0.6" class="hex-symbol-stroke"/>
        <path d="M-7,4 Q-5,2 -3,4 Q-1,6 1,4 Q3,2 5,4" stroke-width="1.8" fill="none" class="hex-symbol-stroke"/>
        <path d="M-5,2 Q-3,4 -1,2 Q1,0 3,2 Q5,4 7,2" stroke-width="1.8" fill="none" class="hex-symbol-stroke"/>
    </symbol>''',
    # Floating boulders
    "floating_rocks": '''<symbol id="sym-floating_rocks" viewBox="-12 -12 24 24">
        <polygon points="-6,-6 -2,-8 0,-5 -3,-3" class="hex-symbol"/>
        <polygon points="3,-4 7,-6 8,-2 5,0 2,-1" class="hex-symbol"/>
        <polygon points="-4,0 -1,-2 2,1 0,4 -3,3" class="hex-symbol"/>
        <path d="M-7,-2 L-4,-2" stroke-width="0.5" stroke-dasharray="1 1" class="hex-symbol-stroke" opacity="0.06"/>
        <path d="M4,2 L6,2" stroke-width="0.5" stroke-dasharray="1 1" class="hex-symbol-stroke" opacity="0.06"/>
    </symbol>''',
    # Buildings / settlement
    "cavern_city": '''<symbol id="sym-cavern_city" viewBox="-12 -12 24 24">
        <rect x="-8" y="-2" width="5" height="8" class="hex-symbol-bold"/>
        <rect x="-6.5" y="0" width="1.5" height="2" class="hex-spot"/>
        <rect x="-2" y="-5" width="4" height="11" class="hex-symbol-bold"/>
        <rect x="-0.5" y="-3" width="1.5" height="2" class="hex-spot"/>
        <rect x="-0.5" y="1" width="1.5" height="2" class="hex-spot"/>
        <rect x="3" y="0" width="5" height="6" class="hex-symbol-bold"/>
        <rect x="4.5" y="2" width="1.5" height="2" class="hex-spot"/>
        <polygon points="-2,-5 0,-7.5 2,-5" class="hex-symbol-bold"/>
    </symbol>''',
    # Single tall tower
    "tower": '''<symbol id="sym-tower" viewBox="-12 -12 24 24">
        <rect x="-2.5" y="-4" width="5" height="10" class="hex-symbol-bold"/>
        <rect x="-4" y="-6" width="8" height="2.5" class="hex-symbol-bold"/>
        <polygon points="-4,-6 0,-9 4,-6" class="hex-symbol-bold"/>
        <rect x="-1.5" y="-3" width="1" height="1.5" class="hex-spot"/>
        <rect x="0.5" y="-3" width="1" height="1.5" class="hex-spot"/>
        <rect x="-1.5" y="0" width="1" height="1.5" class="hex-spot"/>
        <rect x="0.5" y="0" width="1" height="1.5" class="hex-spot"/>
        <rect x="-3.5" y="6" width="7" height="1" class="hex-symbol-bold"/>
    </symbol>''',
    # Fortress — thick walls with corner towers and crenellations
    "fortress": '''<symbol id="sym-fortress" viewBox="-12 -12 24 24">
        <rect x="-8" y="-3" width="16" height="9" class="hex-symbol-bold"/>
        <rect x="-9" y="-7" width="4" height="13" class="hex-symbol-bold"/>
        <rect x="5" y="-7" width="4" height="13" class="hex-symbol-bold"/>
        <rect x="-9.5" y="-8" width="1.5" height="2" class="hex-symbol-bold"/>
        <rect x="-6.5" y="-8" width="1.5" height="2" class="hex-symbol-bold"/>
        <rect x="5.5" y="-8" width="1.5" height="2" class="hex-symbol-bold"/>
        <rect x="8" y="-8" width="1.5" height="2" class="hex-symbol-bold"/>
        <rect x="-7.5" y="-1" width="2" height="2.5" class="hex-spot"/>
        <rect x="5.5" y="-1" width="2" height="2.5" class="hex-spot"/>
        <rect x="-1.5" y="1" width="3" height="5" class="hex-spot"/>
        <path d="M-1.5,1 L0,-1 L1.5,1" class="hex-symbol-bold"/>
    </symbol>''',
    # Castle — central keep with flanking towers and gate
    "castle": '''<symbol id="sym-castle" viewBox="-12 -12 24 24">
        <rect x="-3" y="-5" width="6" height="11" class="hex-symbol-bold"/>
        <polygon points="-3,-5 0,-9 3,-5" class="hex-symbol-bold"/>
        <rect x="-1" y="-4" width="1" height="1.5" class="hex-spot"/>
        <rect x="0.5" y="-4" width="1" height="1.5" class="hex-spot"/>
        <rect x="-8" y="-3" width="4" height="9" class="hex-symbol-bold"/>
        <rect x="-8.5" y="-4.5" width="1.5" height="2" class="hex-symbol-bold"/>
        <rect x="-5.5" y="-4.5" width="1.5" height="2" class="hex-symbol-bold"/>
        <rect x="4" y="-3" width="4" height="9" class="hex-symbol-bold"/>
        <rect x="4.5" y="-4.5" width="1.5" height="2" class="hex-symbol-bold"/>
        <rect x="7" y="-4.5" width="1.5" height="2" class="hex-symbol-bold"/>
        <rect x="-6.5" y="0" width="1.5" height="2" class="hex-spot"/>
        <rect x="5.5" y="0" width="1.5" height="2" class="hex-spot"/>
        <rect x="-1" y="2" width="2.5" height="4" class="hex-spot"/>
    </symbol>''',
}

# --- Overlay symbols (keeper-only, drawn with highlight color) ---

_HEX_OVERLAY_SYMBOLS = {
    # Broken walls / arches
    "ruins": '''<symbol id="ovl-ruins" viewBox="-12 -12 24 24">
        <rect x="-8" y="-2" width="2.5" height="8" class="hex-overlay"/>
        <rect x="-8" y="-4" width="4" height="2" class="hex-overlay"/>
        <rect x="5" y="0" width="2.5" height="6" class="hex-overlay"/>
        <rect x="4" y="-2" width="4" height="2" class="hex-overlay"/>
        <path d="M-4,-3 Q0,-7 4,-3" stroke-width="1.5" fill="none" class="hex-overlay-stroke"/>
        <rect x="-3" y="3" width="2" height="3" class="hex-overlay"/>
        <rect x="1" y="4" width="1.5" height="2" class="hex-overlay"/>
    </symbol>''',
    # Small cluster of huts / houses
    "dwellings": '''<symbol id="ovl-dwellings" viewBox="-12 -12 24 24">
        <rect x="-7" y="0" width="5" height="5" class="hex-overlay"/>
        <polygon points="-7,0 -4.5,-3 -2,0" class="hex-overlay"/>
        <rect x="1" y="1" width="4" height="4" class="hex-overlay"/>
        <polygon points="1,1 3,-2 5,1" class="hex-overlay"/>
        <rect x="-3" y="3" width="3" height="3" class="hex-overlay"/>
        <polygon points="-3,3 -1.5,1 0,3" class="hex-overlay"/>
    </symbol>''',
    # Obelisk / standing stone
    "monument": '''<symbol id="ovl-monument" viewBox="-12 -12 24 24">
        <rect x="-4" y="5" width="8" height="1.5" class="hex-overlay"/>
        <rect x="-2" y="-6" width="4" height="11" class="hex-overlay"/>
        <polygon points="-2,-6 0,-9 2,-6" class="hex-overlay"/>
        <circle cx="0" cy="-2" r="1" class="hex-overlay-spot"/>
    </symbol>''',
    # Warning triangle
    "hazard": '''<symbol id="ovl-hazard" viewBox="-12 -12 24 24">
        <polygon points="0,-8 8,6 -8,6" stroke-width="1.5" fill="none" class="hex-overlay-stroke"/>
        <line x1="0" y1="-3" x2="0" y2="1" stroke-width="2" class="hex-overlay-stroke"/>
        <circle cx="0" cy="3.5" r="1" class="hex-overlay"/>
    </symbol>''',
    # Spiral / dark swirl
    "curse": '''<symbol id="ovl-curse" viewBox="-12 -12 24 24">
        <path d="M0,0 Q0,-3 3,-3 Q6,-3 6,0 Q6,4 -1,4 Q-7,4 -7,-2 Q-7,-7 0,-7 Q8,-7 8,1" stroke-width="1.8" fill="none" class="hex-overlay-stroke"/>
        <circle cx="0" cy="0" r="1.2" class="hex-overlay"/>
    </symbol>''',
    # Eye symbol
    "sanctum": '''<symbol id="ovl-sanctum" viewBox="-12 -12 24 24">
        <path d="M-9,0 Q-4,-6 0,-6 Q4,-6 9,0 Q4,6 0,6 Q-4,6 -9,0 Z" stroke-width="1.5" fill="none" class="hex-overlay-stroke"/>
        <circle cx="0" cy="0" r="3" class="hex-overlay"/>
        <circle cx="0" cy="0" r="1.2" class="hex-overlay-spot"/>
    </symbol>''',
    # Star / mythical mark
    "myth": '''<symbol id="ovl-myth" viewBox="-12 -12 24 24">
        <polygon points="0,-9 2.5,-3 9,-3 4,1.5 6,8 0,4 -6,8 -4,1.5 -9,-3 -2.5,-3" stroke-width="1.2" fill="none" class="hex-overlay-stroke"/>
        <circle cx="0" cy="0" r="1.5" class="hex-overlay"/>
    </symbol>''',
}

# --- River rendering helpers ---

_NEIGHBOR_OFFSETS_EVEN = {
    0: (1, 0), 1: (0, 1), 2: (-1, 0),
    3: (-1, -1), 4: (0, -1), 5: (1, -1),
}
_NEIGHBOR_OFFSETS_ODD = {
    0: (1, 1), 1: (0, 1), 2: (-1, 1),
    3: (-1, 0), 4: (0, -1), 5: (1, 0),
}


def _get_hex_neighbor(col: int, row: int, edge: int) -> tuple[int, int]:
    """Get neighbor coordinates for a given edge direction (flat-top hex)."""
    offsets = _NEIGHBOR_OFFSETS_EVEN if col % 2 == 0 else _NEIGHBOR_OFFSETS_ODD
    dc, dr = offsets[edge]
    return col + dc, row + dr


def _find_shared_edge(c1: int, r1: int, c2: int, r2: int) -> int | None:
    """Find which edge of hex (c1,r1) faces hex (c2,r2). Returns None if not adjacent."""
    for edge in range(6):
        nc, nr = _get_hex_neighbor(c1, r1, edge)
        if nc == c2 and nr == r2:
            return edge
    return None


def get_adjacent_hexes(col: int, row: int, cols: int = 12, rows: int = 12) -> set[str]:
    """Return 'col,row' strings for valid hexes adjacent to the given hex."""
    result = set()
    for edge in range(6):
        nc, nr = _get_hex_neighbor(col, row, edge)
        if 0 <= nc < cols and 0 <= nr < rows:
            result.add(f"{nc},{nr}")
    return result


def _edge_midpoint_abs(cx: float, cy: float, edge: int, size: float) -> tuple[float, float]:
    """Edge midpoint in absolute coordinates."""
    a1 = math.radians(60 * edge)
    a2 = math.radians(60 * ((edge + 1) % 6))
    mx = cx + size * (math.cos(a1) + math.cos(a2)) / 2
    my = cy + size * (math.sin(a1) + math.sin(a2)) / 2
    return mx, my


def _hex_center(col: int, row: int, hex_size: float, margin: float) -> tuple[float, float]:
    """Compute the center of a hex in absolute SVG coordinates."""
    hex_h = _SQRT3 * hex_size
    cx = margin + hex_size + col * 1.5 * hex_size
    cy = margin + hex_h / 2 + row * hex_h + (col % 2) * hex_h / 2
    return cx, cy


def _river_endpoint_edge(col: int, row: int, through_edge: int,
                         hexes: dict, cols: int, rows: int) -> int:
    """Find where a river extends at the start/end of a sequence.

    through_edge: the edge connecting to the next/prev hex in the sequence.
    Returns the edge for the other end (border, lake, or opposite).
    """
    opposite = (through_edge + 3) % 6
    # Prefer: opposite if it's a border or lake, then nearby borders/lakes, then opposite
    for delta in [0, 1, -1, 2, -2]:
        candidate = (opposite + delta) % 6
        nc, nr = _get_hex_neighbor(col, row, candidate)
        if nc < 0 or nc >= cols or nr < 0 or nr >= rows:
            return candidate  # border
        if hexes.get(f"{nc},{nr}") == "lake":
            return candidate  # lake
    return opposite


def _render_rivers(rivers: list[list[str]], hexes: dict,
                   cols: int, rows: int, hex_size: float, margin: float) -> list[str]:
    """Generate SVG paths for river sequences.

    Supports forks/confluences: when multiple rivers share a hex, the branch
    endpoints connect at the hex center rather than extending to an edge.
    """
    # Find fork/confluence hexes (appear in more than one river)
    hex_river_count: dict[str, int] = {}
    for river in rivers:
        for key in river:
            hex_river_count[key] = hex_river_count.get(key, 0) + 1
    fork_hexes = {k for k, v in hex_river_count.items() if v > 1}

    parts = []
    for river in rivers:
        if len(river) < 2:
            continue

        # Parse hex coordinates and compute centers
        coords = []
        for key in river:
            c, r = map(int, key.split(","))
            cx, cy = _hex_center(c, r, hex_size, margin)
            coords.append((c, r, cx, cy))

        # Find shared edges between consecutive hexes
        shared_edges = []
        for i in range(len(coords) - 1):
            edge = _find_shared_edge(coords[i][0], coords[i][1],
                                     coords[i + 1][0], coords[i + 1][1])
            shared_edges.append(edge)

        # Skip if any pair isn't adjacent
        if None in shared_edges:
            continue

        # Compute edge midpoints between consecutive hexes
        edge_mids = []
        for i, edge in enumerate(shared_edges):
            mx, my = _edge_midpoint_abs(coords[i][2], coords[i][3], edge, hex_size)
            edge_mids.append((mx, my))

        # Start point
        c0, r0, cx0, cy0 = coords[0]
        if river[0] in fork_hexes:
            # Fork/confluence: start at hex center for a clean junction
            sx, sy = cx0, cy0
        else:
            start_edge = _river_endpoint_edge(c0, r0, shared_edges[0], hexes, cols, rows)
            sx, sy = _edge_midpoint_abs(cx0, cy0, start_edge, hex_size)

        # End point
        cn, rn, cxn, cyn = coords[-1]
        if river[-1] in fork_hexes:
            # Fork/confluence: end at hex center
            ex, ey = cxn, cyn
        else:
            last_entry = (shared_edges[-1] + 3) % 6
            end_edge = _river_endpoint_edge(cn, rn, last_entry, hexes, cols, rows)
            ex, ey = _edge_midpoint_abs(cxn, cyn, end_edge, hex_size)

        # Build SVG path
        d = f"M{sx:.1f},{sy:.1f}"
        d += f" Q{cx0:.1f},{cy0:.1f} {edge_mids[0][0]:.1f},{edge_mids[0][1]:.1f}"
        for i in range(1, len(edge_mids)):
            d += f" Q{coords[i][2]:.1f},{coords[i][3]:.1f} {edge_mids[i][0]:.1f},{edge_mids[i][1]:.1f}"
        d += f" Q{cxn:.1f},{cyn:.1f} {ex:.1f},{ey:.1f}"

        parts.append(f'<path d="{d}" class="hex-river"/>')

    return parts


def _hex_vertices(cx: float, cy: float, size: float) -> str:
    """Compute flat-top hex polygon points string."""
    points = []
    for i in range(6):
        angle = math.radians(60 * i)
        x = cx + size * math.cos(angle)
        y = cy + size * math.sin(angle)
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)


def render_hex_map(
    hexes: dict | None = None,
    rivers: list[list[str]] | None = None,
    overlays: dict | None = None,
    barriers: dict | None = None,
    cols: int = 12,
    rows: int = 12,
    hex_size: float = 30,
    edit_mode: bool = False,
    is_keeper: bool = False,
    show_overlays: bool = False,
    party_location: str = "",
    party_trail: list[str] | None = None,
    adjacent_hexes: set[str] | None = None,
    timeline_locations: list[tuple[str, str]] | None = None,
    notes: dict | None = None,
) -> Markup:
    """Render a hex map as inline SVG with flat-top hexes.

    hexes: dict mapping "col,row" to symbol_id strings.
    rivers: list of river sequences (each a list of "col,row" strings).
    overlays: dict mapping "col,row" to overlay symbol_id strings (keeper-only).
    barriers: dict mapping "col,row" to list of edge indices (0-5) (keeper-only).
    edit_mode: if True, hexes are clickable (phx-click events).
    is_keeper: if True and not edit_mode, all hexes are clickable for the keeper.
    show_overlays: if True, render overlay symbols and barriers on top.
    party_location: "col,row" of current party position.
    party_trail: list of recent past "col,row" positions (oldest first).
    adjacent_hexes: set of "col,row" strings for movement targets.
    timeline_locations: list of (entry_id, location) for hover highlights.
    """
    if hexes is None:
        hexes = {}
    if rivers is None:
        rivers = []
    if overlays is None:
        overlays = {}
    if barriers is None:
        barriers = {}

    hex_h = _SQRT3 * hex_size
    margin = hex_size * 0.5

    # SVG dimensions
    total_w = (cols - 1) * 1.5 * hex_size + 2 * hex_size + 2 * margin
    total_h = rows * hex_h + hex_h / 2 + 2 * margin

    parts = [
        f'<svg viewBox="0 0 {total_w:.0f} {total_h:.0f}" '
        f'xmlns="http://www.w3.org/2000/svg" class="w-full h-auto max-h-[80vh]">',
        '<style>',
        '  .hex-fill { fill: var(--color-base-200); }',
        '  .hex-stroke { stroke: var(--color-base-content); stroke-width: 1.5; fill: none; opacity: 0.2; }',
        '  .hex-symbol { fill: var(--color-base-content); opacity: 0.35; }',
        '  .hex-symbol-stroke { stroke: var(--color-base-content); opacity: 0.35; }',
        '  .hex-spot { fill: var(--color-base-200); }',
        '  .hex-symbol-bold { fill: var(--color-base-content); opacity: 0.55; }',
        '  .hex-symbol-stroke-bold { stroke: var(--color-base-content); opacity: 0.55; }',
        '  .hex-river { stroke: var(--color-base-content); opacity: 0.35;'
        ' stroke-width: 4.5; fill: none; stroke-linecap: round; }',
        '  .hex-overlay { fill: var(--color-primary); }',
        '  .hex-overlay-stroke { stroke: var(--color-primary); }',
        '  .hex-overlay-spot { fill: var(--color-base-200); }',
        '  .hex-barrier { stroke: var(--color-primary); stroke-width: 3; stroke-linecap: round; }',
        '  @keyframes marker-pulse { 0%,100% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.4); opacity: 0.5; } }',
        '  .party-marker { animation: marker-pulse 2s ease-in-out infinite; transform-origin: center; transform-box: fill-box; }',
        '  .timeline-highlight { opacity: 0; pointer-events: none; }',
        '  .timeline-highlight.active { opacity: 1; }',
        '  .hex-move { cursor: pointer; }',
        '  .hex-move:hover .hex-fill { fill: var(--color-secondary); opacity: 0.15; }',
    ]
    if edit_mode:
        parts.append('  .hex-click { cursor: pointer; }')
        parts.append('  .hex-click:hover .hex-fill { fill: var(--color-base-300); }')
    parts.extend([
        '</style>',
        '<defs>',
    ])

    # Add symbol definitions
    for sym_svg in _HEX_SYMBOLS.values():
        parts.append(sym_svg)
    if show_overlays:
        for sym_svg in _HEX_OVERLAY_SYMBOLS.values():
            parts.append(sym_svg)
    parts.append('</defs>')

    # Draw hexes
    sym_size = hex_size * 1.6
    for col in range(cols):
        for row in range(rows):
            cx = margin + hex_size + col * 1.5 * hex_size
            cy = margin + hex_h / 2 + row * hex_h + (col % 2) * hex_h / 2
            key = f"{col},{row}"
            symbol_id = hexes.get(key)

            points = _hex_vertices(cx, cy, hex_size)

            is_movable = (
                not edit_mode and adjacent_hexes is not None
                and key in adjacent_hexes
            )
            if edit_mode:
                parts.append(
                    f'<g class="hex-click" data-col="{col}" data-row="{row}" data-edit="1">'
                )
            elif is_keeper:
                move_attr = ' data-move="1"' if is_movable else ''
                css = "hex-move" if is_movable else "hex-click"
                parts.append(
                    f'<g class="{css}" data-col="{col}" data-row="{row}"{move_attr}>'
                )
            elif is_movable:
                parts.append(
                    f'<g class="hex-move" data-col="{col}" data-row="{row}" data-move="1">'
                )

            parts.append(f'<polygon points="{points}" class="hex-fill"/>')
            parts.append(f'<polygon points="{points}" class="hex-stroke"/>')

            if symbol_id and symbol_id != "river" and symbol_id in _HEX_SYMBOLS:
                parts.append(
                    f'<use href="#sym-{symbol_id}" '
                    f'x="{cx - sym_size / 2:.1f}" y="{cy - sym_size / 2:.1f}" '
                    f'width="{sym_size:.1f}" height="{sym_size:.1f}"/>'
                )

            if edit_mode or is_keeper or is_movable:
                parts.append('</g>')

    # Draw rivers (after all hexes, as overlay)
    parts.extend(_render_rivers(rivers, hexes, cols, rows, hex_size, margin))

    # Draw party location marker (ball only, wrapped in group for JS toggling)
    if party_location:
        parts.append('<g id="party-location">')
        try:
            pc, pr = map(int, party_location.split(","))
            pcx, pcy = _hex_center(pc, pr, hex_size, margin)
            r = hex_size * 0.18
            parts.append(
                f'<circle cx="{pcx:.1f}" cy="{pcy:.1f}" r="{r:.1f}" '
                f'class="party-marker" fill="var(--color-secondary)"/>'
            )
        except (ValueError, AttributeError):
            pass
        parts.append('</g>')

    # Draw timeline highlight groups (hidden, shown on hover via JS)
    if timeline_locations:
        r = hex_size * 0.18
        for tl_idx, (entry_id, loc) in enumerate(timeline_locations):
            if not loc:
                continue
            try:
                fc, fr = map(int, loc.split(","))
                fcx, fcy = _hex_center(fc, fr, hex_size, margin)
                parts.append(
                    f'<g class="timeline-highlight" data-entry-id="{entry_id}">'
                    f'<circle cx="{fcx:.1f}" cy="{fcy:.1f}" r="{r:.1f}" '
                    f'class="party-marker" fill="var(--color-secondary)"/></g>'
                )
            except (ValueError, AttributeError):
                continue

    # Draw overlay symbols and barriers (keeper-only layer, on top of everything)
    if show_overlays:
        if overlays:
            ovl_size = hex_size * 1.4
            for col in range(cols):
                for row in range(rows):
                    key = f"{col},{row}"
                    ovl_id = overlays.get(key)
                    if ovl_id and ovl_id in _HEX_OVERLAY_SYMBOLS:
                        cx = margin + hex_size + col * 1.5 * hex_size
                        cy = margin + hex_h / 2 + row * hex_h + (col % 2) * hex_h / 2
                        parts.append(
                            f'<use href="#ovl-{ovl_id}" '
                            f'x="{cx - ovl_size / 2:.1f}" y="{cy - ovl_size / 2:.1f}" '
                            f'width="{ovl_size:.1f}" height="{ovl_size:.1f}" '
                            f'style="pointer-events:none"/>'
                        )

        if barriers:
            for col in range(cols):
                for row in range(rows):
                    key = f"{col},{row}"
                    edges = barriers.get(key)
                    if not edges:
                        continue
                    cx = margin + hex_size + col * 1.5 * hex_size
                    cy = margin + hex_h / 2 + row * hex_h + (col % 2) * hex_h / 2
                    for edge_i in edges:
                        angle1 = math.radians(60 * edge_i)
                        angle2 = math.radians(60 * ((edge_i + 1) % 6))
                        x1 = cx + hex_size * math.cos(angle1)
                        y1 = cy + hex_size * math.sin(angle1)
                        x2 = cx + hex_size * math.cos(angle2)
                        y2 = cy + hex_size * math.sin(angle2)
                        parts.append(
                            f'<line x1="{x1:.1f}" y1="{y1:.1f}" '
                            f'x2="{x2:.1f}" y2="{y2:.1f}" '
                            f'class="hex-barrier" style="pointer-events:none"/>'
                        )

    # Note markers (small dot in top-right corner, shown in overlay mode)
    if show_overlays and notes:
        r = hex_size * 0.12
        for key, note_text in notes.items():
            if not note_text or not note_text.strip():
                continue
            try:
                c, rw = map(int, key.split(","))
            except (ValueError, AttributeError):
                continue
            if c < 0 or c >= cols or rw < 0 or rw >= rows:
                continue
            cx = margin + hex_size + c * 1.5 * hex_size
            cy = margin + hex_h / 2 + rw * hex_h + (c % 2) * hex_h / 2
            # Top-right vertex of flat-top hex is at -60° (300°), inset slightly
            angle = math.radians(-60)
            dx = hex_size * 0.8 * math.cos(angle)
            dy = hex_size * 0.8 * math.sin(angle)
            parts.append(
                f'<circle cx="{cx + dx:.1f}" cy="{cy + dy:.1f}" r="{r:.1f}" '
                f'class="hex-overlay" style="pointer-events:none"/>'
            )

    parts.append('</svg>')
    return Markup('\n'.join(parts))


def _extract_symbol_content(symbol_svg: str) -> str:
    """Extract the inner content from a <symbol> element."""
    # Remove <symbol ...> opening and </symbol> closing tags
    content = re.sub(r'<symbol[^>]*>', '', symbol_svg)
    content = content.replace('</symbol>', '')
    return content.strip()


def render_hex_palette(active_symbol: str = "") -> Markup:
    """Render the symbol palette for hex map editing."""
    palette_style = (
        '<style>'
        '.pal-sym { fill: currentColor; opacity: 0.5; }'
        '.pal-sym-stroke { stroke: currentColor; opacity: 0.5; fill: none; }'
        '.pal-spot { fill: var(--color-base-100); }'
        '</style>'
    )
    items = [palette_style]
    # Eraser option
    eraser_active = "btn-primary" if active_symbol == "" else "btn-ghost"
    items.append(
        f'<button class="btn btn-sm {eraser_active} w-full justify-start gap-2" '
        f'phx-click="select_map_symbol" phx-value-symbol="">'
        f'<svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2">'
        f'<path d="M18 6L6 18M6 6l12 12"/>'
        f'</svg>'
        f'Eraser</button>'
    )
    for sym_id, label in HEX_SYMBOL_LABELS.items():
        active_cls = "btn-primary" if active_symbol == sym_id else "btn-ghost"
        inner = _extract_symbol_content(_HEX_SYMBOLS[sym_id])
        # Replace hex-symbol/hex-spot classes with palette classes for visibility
        inner = inner.replace('class="hex-symbol-stroke-bold"', 'class="pal-sym-stroke"')
        inner = inner.replace('class="hex-symbol-bold"', 'class="pal-sym"')
        inner = inner.replace('class="hex-symbol-stroke"', 'class="pal-sym-stroke"')
        inner = inner.replace('class="hex-symbol"', 'class="pal-sym"')
        inner = inner.replace('class="hex-spot"', 'class="pal-spot"')
        items.append(
            f'<button class="btn btn-sm {active_cls} w-full justify-start gap-2" '
            f'phx-click="select_map_symbol" phx-value-symbol="{sym_id}">'
            f'<svg viewBox="-12 -12 24 24" class="h-5 w-5" xmlns="http://www.w3.org/2000/svg">'
            f'{inner}'
            f'</svg>'
            f'{label}</button>'
        )
    return Markup('\n'.join(items))


def render_overlay_palette(active_overlay: str = "") -> Markup:
    """Render the overlay symbol palette for hex map editing (keeper-only)."""
    palette_style = (
        '<style>'
        '.pal-ovl { fill: var(--color-primary); opacity: 0.7; }'
        '.pal-ovl-stroke { stroke: var(--color-primary); opacity: 0.7; fill: none; }'
        '.pal-ovl-spot { fill: var(--color-base-100); }'
        '</style>'
    )
    items = [palette_style]
    # Eraser option
    eraser_active = "btn-primary" if active_overlay == "" else "btn-ghost"
    items.append(
        f'<button class="btn btn-sm {eraser_active} w-full justify-start gap-2" '
        f'phx-click="select_overlay_symbol" phx-value-symbol="">'
        f'<svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2">'
        f'<path d="M18 6L6 18M6 6l12 12"/>'
        f'</svg>'
        f'Eraser</button>'
    )
    for sym_id, label in HEX_OVERLAY_LABELS.items():
        active_cls = "btn-primary" if active_overlay == sym_id else "btn-ghost"
        inner = _extract_symbol_content(_HEX_OVERLAY_SYMBOLS[sym_id])
        inner = inner.replace('class="hex-overlay-stroke"', 'class="pal-ovl-stroke"')
        inner = inner.replace('class="hex-overlay"', 'class="pal-ovl"')
        inner = inner.replace('class="hex-overlay-spot"', 'class="pal-ovl-spot"')
        items.append(
            f'<button class="btn btn-sm {active_cls} w-full justify-start gap-2" '
            f'phx-click="select_overlay_symbol" phx-value-symbol="{sym_id}">'
            f'<svg viewBox="-12 -12 24 24" class="h-5 w-5" xmlns="http://www.w3.org/2000/svg">'
            f'{inner}'
            f'</svg>'
            f'{label}</button>'
        )
    # Barrier edge buttons
    _barrier_labels = {
        0: "Barrier Right",
        1: "Barrier Bottom-R",
        2: "Barrier Bottom-L",
        3: "Barrier Left",
        4: "Barrier Top-L",
        5: "Barrier Top-R",
    }
    items.append('<div class="divider my-1"></div>')
    items.append('<h4 class="font-bold text-xs mb-1">Barriers</h4>')
    barrier_eraser_active = "btn-primary" if active_overlay == "barrier_eraser" else "btn-ghost"
    items.append(
        f'<button class="btn btn-sm {barrier_eraser_active} w-full justify-start gap-2" '
        f'phx-click="select_overlay_symbol" phx-value-symbol="barrier_eraser">'
        f'<svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2">'
        f'<path d="M18 6L6 18M6 6l12 12"/>'
        f'</svg>'
        f'Remove Barrier</button>'
    )
    _pr = 9
    _pverts = [(math.cos(math.radians(60 * i)) * _pr, math.sin(math.radians(60 * i)) * _pr) for i in range(6)]
    _phex_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in _pverts)
    for edge_i, label in _barrier_labels.items():
        bid = f"barrier_{edge_i}"
        active_cls = "btn-primary" if active_overlay == bid else "btn-ghost"
        x1, y1 = _pverts[edge_i]
        x2, y2 = _pverts[(edge_i + 1) % 6]
        items.append(
            f'<button class="btn btn-sm {active_cls} w-full justify-start gap-2" '
            f'phx-click="select_overlay_symbol" phx-value-symbol="{bid}">'
            f'<svg viewBox="-12 -12 24 24" class="h-5 w-5" xmlns="http://www.w3.org/2000/svg">'
            f'<polygon points="{_phex_pts}" fill="none" stroke="currentColor" stroke-width="1" opacity="0.3"/>'
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="var(--color-primary)" stroke-width="3" stroke-linecap="round"/>'
            f'</svg>'
            f'{label}</button>'
        )
    return Markup('\n'.join(items))
