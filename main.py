from ui.main_window import MainWindow
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
import sys
import os
from backend.icon_utils import load_app_icon
from backend.config import get_config
from backend.theme import render_stylesheet
from backend.resource_utils import get_style_path

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application icon
    app_icon = load_app_icon()
    
    if app_icon and not app_icon.isNull():
        app.setWindowIcon(app_icon)
        # Force refresh
        app.processEvents()
    
    # Load and apply global stylesheet with theming
    try:
        qss_path = get_style_path()
        with open(qss_path, "r") as f:
            qss_text = f.read()
        theme = get_config().get('theme', 'dark')
        app.setStyleSheet(render_stylesheet(qss_text, theme))
    except Exception as e:
        print(f"Warning: Could not load style.qss: {e}")
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 