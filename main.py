from ui.main_window import MainWindow
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
import sys
import os
from backend.icon_utils import load_app_icon

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application icon
    app_icon = load_app_icon()
    
    if app_icon and not app_icon.isNull():
        app.setWindowIcon(app_icon)
        # Force refresh
        app.processEvents()
    
    # Load and apply global stylesheet
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        qss_path = os.path.join(base_dir, 'style.qss')
        with open(qss_path, "r") as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        print(f"Warning: Could not load style.qss: {e}")
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 