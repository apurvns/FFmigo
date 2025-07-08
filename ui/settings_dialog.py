from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox
from PyQt6.QtCore import pyqtSignal
import subprocess
import os

class SettingsDialog(QDialog):
    settings_saved = pyqtSignal(dict)

    def __init__(self, settings=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        # LLM API endpoint
        layout.addWidget(QLabel("LLM API Endpoint:"))
        self.llm_endpoint = QLineEdit()
        layout.addWidget(self.llm_endpoint)
        # LLM model name
        layout.addWidget(QLabel("LLM Model Name:"))
        self.llm_model = QLineEdit()
        layout.addWidget(self.llm_model)
        # FFmpeg path
        ffmpeg_row = QHBoxLayout()
        ffmpeg_row.addWidget(QLabel("FFmpeg Path:"))
        self.ffmpeg_path = QLineEdit()
        ffmpeg_row.addWidget(self.ffmpeg_path)
        browse_ffmpeg = QPushButton("Browse")
        browse_ffmpeg.clicked.connect(self.browse_ffmpeg)
        ffmpeg_row.addWidget(browse_ffmpeg)
        test_ffmpeg = QPushButton("Test")
        test_ffmpeg.clicked.connect(self.test_ffmpeg)
        ffmpeg_row.addWidget(test_ffmpeg)
        layout.addLayout(ffmpeg_row)
        self.ffmpeg_test_result = QLabel()
        layout.addWidget(self.ffmpeg_test_result)
        # Export dir
        export_row = QHBoxLayout()
        export_row.addWidget(QLabel("Default Export Directory:"))
        self.export_dir = QLineEdit()
        export_row.addWidget(self.export_dir)
        browse_export = QPushButton("Browse")
        browse_export.clicked.connect(self.browse_export)
        export_row.addWidget(browse_export)
        layout.addLayout(export_row)
        # Buttons
        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)
        # Load settings
        if settings:
            self.llm_endpoint.setText(settings.get('llm_endpoint', ''))
            self.llm_model.setText(settings.get('llm_model', ''))
            self.ffmpeg_path.setText(settings.get('ffmpeg_path', ''))
            self.export_dir.setText(settings.get('export_dir', ''))

    def browse_ffmpeg(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select FFmpeg Executable")
        if path:
            self.ffmpeg_path.setText(path)

    def test_ffmpeg(self):
        path = self.ffmpeg_path.text().strip()
        if not path:
            self.ffmpeg_test_result.setText("No path specified.")
            return
        try:
            result = subprocess.run([path, '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            if result.returncode == 0:
                self.ffmpeg_test_result.setText("FFmpeg OK: " + result.stdout.split('\n')[0])
            else:
                self.ffmpeg_test_result.setText("Error: " + result.stderr)
        except Exception as e:
            self.ffmpeg_test_result.setText(f"Error: {e}")

    def browse_export(self):
        path = QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if path:
            self.export_dir.setText(path)

    def save(self):
        settings = {
            'llm_endpoint': self.llm_endpoint.text().strip(),
            'llm_model': self.llm_model.text().strip(),
            'ffmpeg_path': self.ffmpeg_path.text().strip(),
            'export_dir': self.export_dir.text().strip(),
        }
        self.settings_saved.emit(settings)
        self.accept() 