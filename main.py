from ui.main_window import MainWindow
from PyQt6.QtWidgets import QApplication
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Load and apply global stylesheet
    try:
        with open("style.qss", "r") as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        print(f"Warning: Could not load style.qss: {e}")
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 