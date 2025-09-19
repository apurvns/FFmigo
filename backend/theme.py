import re
from typing import Dict


# This module enables runtime theming without editing QSS to add variables.
# It maps known dark-theme hex colors from style.qss to light-theme equivalents.


DARK_TO_LIGHT_MAP: Dict[str, str] = {
    # Core surfaces
    "#18141d": "#ffffff",  # BG
    "#120e17": "#f7f7fb",  # BG_SUNK
    "#221a2c": "#f9f9fb",  # BG_ELEVATED_ALT
    "#3a2e4a": "#d0d0d8",  # BG_HOVER / BORDER
    
    # Text
    "#e6eaf3": "#1c1c1e",  # TEXT
    "#ffffff": "#1c1c1e",  # TEXT_INVERTED (dark text on light bg)
    "#fff": "#1c1c1e",     # TEXT_INVERTED_SHORT (dark text on light bg)
    "#b6b1c9": "#4a4a4f",  # TEXT_MUTED
    "#8a7c9a": "#6b6b70",  # TEXT_SUBTLE
    
    # Greys and borders
    "#444444": "#e6e6ee",  # BORDER_MUTED
    "#333333": "#d1d5db",  # CODE_BORDER
    "#444": "#d1d5db",     # SHORT BORDER
    "#666666": "#4b5563",  # MUTED_666
    "#888888": "#6b7280",  # MUTED_888
    "#aaa": "#9ca3af",     # MUTED_AAA
    "#ddd": "#d1d5db",     # PROGRESS_BORDER
    "#000000": "#000000",

    # Accent / interactive  
    "#a259ff": "#d0d0d8",  # ACCENT - use border color for both background and border in light theme hover
    "#b366ff": "#e8e8f0",  # ACCENT_HOVER - slightly darker light for light theme  
    "#8b4dff": "#d8d8e0",  # ACCENT_ACTIVE - medium light for light theme active
    "#6a3ea1": "#e0e0e8",  # ACCENT_ALT - light gray for light theme
    "#4a3e5a": "#f0f0f8",  # INTERACTIVE_BG (lighter)
    "#6a5e7a": "#e0e0e8",  # INTERACTIVE_ACTIVE (lighter)
    "#5a4e6a": "#d0d0d8",  # BORDER color for buttons

    # Player specific - black stays black

    # Chat/code colors
    "#00ff00": "#047857",  # CODE_USER
    "#00aaff": "#2563eb",  # CODE_CMD
    "#ff4444": "#dc2626",  # CODE_ERR

    # Progress/dialogs
    # handled via greys above

    # Status colors
    "#dc3545": "#d32f2f",  # ERROR
    "#c82333": "#b71c1c",  # ERROR_HOVER
    "#6c757d": "#6b7280",  # WARNING
    "#28a745": "#2e7d32",  # SUCCESS
    "#218838": "#1b5e20",  # SUCCESS_HOVER

    # Brands (kept but slight tweaks for GitHub contrast)
    "#1DA1F2": "#1DA1F2",
    "#1a8cd8": "#1a8cd8",
    "#333333": "#24292e",
    "#555555": "#2f353b",
    "#6C757D": "#6B7280",
    "#5a6268": "#4b5563",
    "#8a4fd8": "#6a2df0",
    "#2d1e3a": "#e8e8f0",  # BG_ELEVATED (lighter for selected items)
}


def get_theme_color(color_name: str) -> str:
    """Get a color value based on current theme. Returns hex color string."""
    from backend.config import get_config
    config = get_config()
    theme = config.get('theme', 'dark')
    
    # Color mappings for different themes
    color_map = {
        'dark': {
            'selected_bg': '#2d1e3a',
            'icon_color': '#ffffff',
            'text_color': '#e6eaf3',
            'button_bg': '#2d1e3a',
            'button_hover': '#a259ff',
        },
        'light': {
            'selected_bg': '#e8e8f0',
            'icon_color': '#1c1c1e',
            'text_color': '#1c1c1e',
            'button_bg': '#ffffff',
            'button_hover': '#1c1c1e',
            'button_hover_text': '#ffffff',
        }
    }
    
    return color_map.get(theme, color_map['dark']).get(color_name, '#000000')


def render_stylesheet(qss_text: str, theme: str) -> str:
    """Return a themed stylesheet. For 'dark' return input unchanged; for 'light' map hex colors."""
    if theme.lower() == "dark":
        return qss_text

    # Use regex to replace colors properly without conflicts
    import re
    
    # Create a mapping with placeholders to avoid conflicts
    result = qss_text
    placeholder_map = {}
    
    # First pass: replace with unique placeholders
    for i, (dark_color, light_color) in enumerate(DARK_TO_LIGHT_MAP.items()):
        placeholder = f"__PLACEHOLDER_{i}__"
        placeholder_map[placeholder] = light_color
        result = result.replace(dark_color, placeholder)
    
    # Second pass: replace placeholders with final colors
    for placeholder, light_color in placeholder_map.items():
        result = result.replace(placeholder, light_color)
    
    return result


