from ui.main_window import MainWindow
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application icon
    import os
    icon_path = os.path.join(os.path.dirname(__file__), 'ui/resources/icons/app_logo.svg')
    png_icon_path = os.path.join(os.path.dirname(__file__), 'ui/resources/icons/app_logo.png')
    
    # Try to load the icon
    app_icon = None
    
    # Try PNG first (more reliable)
    if os.path.exists(png_icon_path):
        app_icon = QIcon(png_icon_path)
        print(f"Loaded PNG icon: {not app_icon.isNull()}")
    elif os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        print(f"Loaded SVG icon: {not app_icon.isNull()}")
    
    if app_icon and not app_icon.isNull():
        app.setWindowIcon(app_icon)
        print("Application icon set successfully!")
        # Force refresh
        app.processEvents()
    else:
        print("Failed to load application icon!")
    
    # Load and apply global stylesheet
    try:
        with open("style.qss", "r") as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        print(f"Warning: Could not load style.qss: {e}")
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 