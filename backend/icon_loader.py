"""
Centralized SVG icon loader with dynamic theming support.
All icons are loaded from separate SVG files and themed dynamically.
"""
import os
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import QByteArray
from .theme import get_theme_color


class IconLoader:
    """Centralized icon loading with dynamic theming"""
    
    def __init__(self):
        self.icons_dir = os.path.join(os.path.dirname(__file__), '..', 'ui', 'resources', 'icons')
        self._icon_cache = {}
    
    def get_icon(self, icon_name: str, size: int = 24) -> QIcon:
        """
        Load an icon with current theme colors applied.
        
        Args:
            icon_name: Name of the icon file (without .svg extension)
            size: Icon size in pixels
            
        Returns:
            QIcon with theme colors applied
        """
        cache_key = f"{icon_name}_{size}_{self._get_current_theme()}"
        
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]
        
        svg_path = os.path.join(self.icons_dir, f"{icon_name}.svg")
        
        if not os.path.exists(svg_path):
            print(f"Warning: Icon file not found: {svg_path}")
            return QIcon()
        
        # Read SVG content
        with open(svg_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()
        
        # Apply theme colors
        themed_svg = self._apply_theme_colors(svg_content)
        
        # Create QIcon from themed SVG
        icon = self._create_icon_from_svg(themed_svg, size)
        
        # Cache the result
        self._icon_cache[cache_key] = icon
        
        return icon
    
    def _get_current_theme(self) -> str:
        """Get current theme name"""
        from .config import get_config
        config = get_config()
        return config.get('theme', 'dark')
    
    def _apply_theme_colors(self, svg_content: str) -> str:
        """Apply current theme colors to SVG content"""
        icon_color = get_theme_color('icon_color')
        
        # Replace currentColor with actual theme color
        themed_svg = svg_content.replace('fill="currentColor"', f'fill="{icon_color}"')
        themed_svg = themed_svg.replace('stroke="currentColor"', f'stroke="{icon_color}"')
        
        # Debug: print the themed SVG for first icon
        if 'play' in svg_content or 'pause' in svg_content:
            print(f"DEBUG: Icon color: {icon_color}")
            print(f"DEBUG: Themed SVG: {themed_svg[:200]}...")
        
        return themed_svg
    
    def _create_icon_from_svg(self, svg_content: str, size: int) -> QIcon:
        """Create QIcon from SVG content"""
        # Create SVG renderer
        renderer = QSvgRenderer(QByteArray(svg_content.encode('utf-8')))
        
        if not renderer.isValid():
            print(f"Warning: Invalid SVG content")
            return QIcon()
        
        # Create pixmap with transparent background
        from PyQt6.QtGui import QPainter
        from PyQt6.QtCore import Qt
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        # Render SVG to pixmap
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter)
        painter.end()
        
        return QIcon(pixmap)
    
    def clear_cache(self):
        """Clear icon cache (call when theme changes)"""
        self._icon_cache.clear()


# Global instance
_icon_loader = IconLoader()


def get_icon(icon_name: str, size: int = 24) -> QIcon:
    """
    Get a themed icon by name.
    
    Args:
        icon_name: Name of the icon file (without .svg extension)
        size: Icon size in pixels
        
    Returns:
        QIcon with current theme colors applied
    """
    return _icon_loader.get_icon(icon_name, size)


def clear_icon_cache():
    """Clear icon cache (call when theme changes)"""
    _icon_loader.clear_cache()
