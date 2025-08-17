from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox, QComboBox
from PyQt6.QtCore import pyqtSignal
import subprocess
import os
from backend import llm_client

PROVIDER_DEFAULTS = {
    'Ollama': {
        'endpoint': 'http://localhost:11434/api/generate',
        'api_key': '',
        'model': '',
    },
    'OpenAI': {
        'endpoint': 'https://api.openai.com/v1/chat/completions',
        'api_key': '',
        'model': 'gpt-3.5-turbo',
    },
    'Gemini': {
        'endpoint': 'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent',
        'api_key': '',
        'model': 'gemini-pro',
    },
    'Claude': {
        'endpoint': 'https://api.anthropic.com/v1/messages',
        'api_key': '',
        'model': 'claude-3-opus-20240229',
    },
}

class SettingsDialog(QDialog):
    settings_saved = pyqtSignal(dict)

    def __init__(self, settings=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)
        self.setObjectName("SettingsDialog")
        layout = QVBoxLayout(self)
        # Provider selection
        label_provider = QLabel("LLM Provider:")
        label_provider.setObjectName("SettingsLabel")
        layout.addWidget(label_provider)
        self.provider = QComboBox()
        self.provider.setObjectName("ProviderComboBox")
        self.provider.addItems(["Ollama", "OpenAI", "Gemini", "Claude"])
        layout.addWidget(self.provider)
        # API Key (for OpenAI, Gemini, Claude)
        self.label_api_key = QLabel("API Key:")
        self.label_api_key.setObjectName("SettingsLabel")
        self.api_key = QLineEdit()
        self.api_key.setObjectName("ApiKeyInput")
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.label_api_key)
        layout.addWidget(self.api_key)
        # LLM API endpoint
        self.label_llm_endpoint = QLabel("LLM API Endpoint:")
        self.label_llm_endpoint.setObjectName("SettingsLabel")
        self.llm_endpoint = QLineEdit()
        self.llm_endpoint.setObjectName("LlmEndpointInput")
        layout.addWidget(self.label_llm_endpoint)
        layout.addWidget(self.llm_endpoint)
        # LLM model selection (dropdown or text)
        self.label_llm_model = QLabel("LLM Model:")
        self.label_llm_model.setObjectName("SettingsLabel")
        self.llm_model_combo = QComboBox()
        self.llm_model_combo.setObjectName("LlmModelCombo")
        self.llm_model_combo.setEditable(False)
        self.llm_model = QLineEdit()
        self.llm_model.setObjectName("LlmModelInput")
        layout.addWidget(self.label_llm_model)
        layout.addWidget(self.llm_model_combo)
        layout.addWidget(self.llm_model)
        # FFmpeg path
        ffmpeg_row = QHBoxLayout()
        label_ffmpeg = QLabel("FFmpeg Path:")
        label_ffmpeg.setObjectName("SettingsLabel")
        ffmpeg_row.addWidget(label_ffmpeg)
        self.ffmpeg_path = QLineEdit()
        self.ffmpeg_path.setObjectName("FfmpegPathInput")
        ffmpeg_row.addWidget(self.ffmpeg_path)
        browse_ffmpeg = QPushButton("Browse")
        browse_ffmpeg.setObjectName("BrowseFfmpegButton")
        browse_ffmpeg.clicked.connect(self.browse_ffmpeg)
        ffmpeg_row.addWidget(browse_ffmpeg)
        test_ffmpeg = QPushButton("Test")
        test_ffmpeg.setObjectName("TestFfmpegButton")
        test_ffmpeg.clicked.connect(self.test_ffmpeg)
        ffmpeg_row.addWidget(test_ffmpeg)
        layout.addLayout(ffmpeg_row)
        self.ffmpeg_test_result = QLabel()
        self.ffmpeg_test_result.setObjectName("FfmpegTestResult")
        layout.addWidget(self.ffmpeg_test_result)
        # Export dir
        export_row = QHBoxLayout()
        label_export = QLabel("Default Export Directory:")
        label_export.setObjectName("SettingsLabel")
        export_row.addWidget(label_export)
        self.export_dir = QLineEdit()
        self.export_dir.setObjectName("ExportDirInput")
        export_row.addWidget(self.export_dir)
        browse_export = QPushButton("Browse")
        browse_export.setObjectName("BrowseExportButton")
        browse_export.clicked.connect(self.browse_export)
        export_row.addWidget(browse_export)
        layout.addLayout(export_row)
        # Buttons
        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setObjectName("SaveSettingsButton")
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("CancelSettingsButton")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)
        # Load settings
        if settings:
            provider = settings.get('provider', 'Ollama')
            self.provider.setCurrentText(provider)
            self.llm_endpoint.setText(settings.get('llm_endpoint', PROVIDER_DEFAULTS[provider]['endpoint']))
            self.llm_model.setText(settings.get('llm_model', PROVIDER_DEFAULTS[provider]['model']))
            self.api_key.setText(settings.get('api_key', PROVIDER_DEFAULTS[provider]['api_key']))
            self.ffmpeg_path.setText(settings.get('ffmpeg_path', ''))
            self.export_dir.setText(settings.get('export_dir', ''))
        else:
            self.provider.setCurrentText('Ollama')
            self.llm_endpoint.setText(PROVIDER_DEFAULTS['Ollama']['endpoint'])
            self.llm_model.setText(PROVIDER_DEFAULTS['Ollama']['model'])
            self.api_key.setText('')
        
        # Connect provider change signal and initialize UI state
        self.provider.currentTextChanged.connect(self.on_provider_changed)
        self.on_provider_changed(self.provider.currentText(), skip_defaults=True)

    def on_provider_changed(self, provider, skip_defaults=False):
        # Set sensible defaults only if not skipping (i.e., not during initial load)
        if not skip_defaults:
            self.llm_endpoint.setText(PROVIDER_DEFAULTS[provider]['endpoint'])
            self.llm_model.setText(PROVIDER_DEFAULTS[provider]['model'])
            self.api_key.setText(PROVIDER_DEFAULTS[provider]['api_key'])
        if provider == "Ollama":
            self.label_api_key.hide()
            self.api_key.hide()
            self.llm_model.hide()
            self.llm_model_combo.show()
            # Fetch models from Ollama
            endpoint = self.llm_endpoint.text().strip() or PROVIDER_DEFAULTS['Ollama']['endpoint']
            models = llm_client.list_ollama_models(endpoint)
            self.llm_model_combo.clear()
            if models:
                self.llm_model_combo.addItems(models)
            else:
                self.llm_model_combo.addItem("No models found")
            self.label_llm_model.show()
            self.label_llm_endpoint.show()
            self.llm_endpoint.show()
        else:
            self.label_api_key.show()
            self.api_key.show()
            self.llm_model_combo.hide()
            self.llm_model.show()
            self.label_llm_model.show()
            self.label_llm_endpoint.show()
            self.llm_endpoint.show()

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
        provider = self.provider.currentText()
        if provider == "Ollama":
            model = self.llm_model_combo.currentText()
        else:
            model = self.llm_model.text().strip()
        settings = {
            'provider': provider,
            'llm_endpoint': self.llm_endpoint.text().strip(),
            'llm_model': model,
            'api_key': self.api_key.text().strip(),
            'ffmpeg_path': self.ffmpeg_path.text().strip(),
            'export_dir': self.export_dir.text().strip(),
        }
        self.settings_saved.emit(settings)
        self.accept() 