from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QFileDialog, QLineEdit, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QPixmap, QIcon, QDragEnterEvent, QDropEvent, QFont
import os
from backend import project_manager, thumbnailer
from backend import llm_client, ffmpeg_runner
import threading
from ui.settings_dialog import SettingsDialog
from backend import config
import subprocess
import sys

class DragDropWidget(QWidget):
    file_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(300)
        self.setStyleSheet('''
            border: 2px dashed #aaa;
            border-radius: 12px;
            background: #fafbfc;
        ''')
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon = QLabel()
        self.icon.setPixmap(QPixmap(os.path.join(os.path.dirname(__file__), '../resources/icons/film.png')).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio))
        self.text = QLabel("<b>Drag and Drop Your Video File Here</b><br>or click to select a video")
        self.text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon)
        layout.addWidget(self.text)
        self.setLayout(layout)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.file_dropped.emit(file_path)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            file_dialog = QFileDialog(self)
            file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
            file_dialog.setNameFilter("Video Files (*.mp4 *.mov *.avi *.mkv *.webm *.flv *.wmv)")
            if file_dialog.exec():
                selected = file_dialog.selectedFiles()
                if selected:
                    self.file_dropped.emit(selected[0])

class MainWindow(QMainWindow):
    process_result_ready = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("FFMigo Video Editor")
        self.resize(900, 600)
        # Load config
        self.app_config = config.get_config()
        # Main layout
        central = QWidget()
        self.setCentralWidget(central)
        self.vbox = QVBoxLayout(central)
        # Settings button row
        settings_row = QHBoxLayout()
        settings_row.addStretch(1)
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.open_settings)
        settings_row.addWidget(settings_btn)
        
        reopen_btn = QPushButton("Reopen Project")
        reopen_btn.clicked.connect(self.open_project_dialog)
        settings_row.addWidget(reopen_btn)
        self.vbox.addLayout(settings_row)
        # Drag-and-drop area
        self.dragdrop = DragDropWidget()
        self.dragdrop.file_dropped.connect(self.on_file_dropped)
        self.vbox.addWidget(self.dragdrop, stretch=7)
        # Video thumbnail and path display (hidden until video loaded)
        self.video_info_widget = QWidget()
        self.video_info_layout = QHBoxLayout(self.video_info_widget)
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(120, 90)
        self.thumbnail_label.setScaledContents(True)
        self.video_path_label = QLabel()
        self.video_path_label.setWordWrap(True)
        self.video_info_layout.addWidget(self.thumbnail_label)
        self.video_info_layout.addWidget(self.video_path_label)
        self.video_info_widget.hide()
        self.vbox.addWidget(self.video_info_widget, stretch=0)
        # Chat log display
        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setMinimumHeight(120)
        self.vbox.addWidget(self.chat_log, stretch=2)
        # Processed video area
        self.processed_widget = QWidget()
        self.processed_layout = QHBoxLayout(self.processed_widget)
        self.processed_thumb = QLabel()
        self.processed_thumb.setFixedSize(120, 90)
        self.processed_thumb.setScaledContents(True)
        self.processed_path = QLabel()
        self.processed_path.setWordWrap(True)
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.play_processed_video)
        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self.export_processed_video)
        self.processed_layout.addWidget(self.processed_thumb)
        self.processed_layout.addWidget(self.processed_path)
        self.processed_layout.addWidget(self.play_btn)
        self.processed_layout.addWidget(self.export_btn)
        self.processed_widget.hide()
        self.vbox.addWidget(self.processed_widget, stretch=0)
        # Chat input area
        chat_area = QWidget()
        chat_layout = QHBoxLayout(chat_area)
        self.chat_input = QTextEdit()
        self.chat_input.setPlaceholderText("Type your video editing command here...")
        self.chat_input.setFixedHeight(60)
        self.chat_input.setDisabled(True)
        self.send_btn = QPushButton("Send")
        self.send_btn.setDisabled(True)
        self.send_btn.clicked.connect(self.on_send_clicked)
        chat_layout.addWidget(self.chat_input, stretch=1)
        chat_layout.addWidget(self.send_btn)
        self.vbox.addWidget(chat_area, stretch=3)
        # State
        self.project_dir = None
        self.input_path = None
        self.input_ext = None
        self.processed_path_file = None
        self.process_result_ready.connect(self.on_process_result_ready)

    def on_file_dropped(self, file_path):
        # Create project dir and copy video
        self.project_dir = project_manager.create_project_dir()
        self.input_path = project_manager.copy_video_to_project(file_path, self.project_dir)
        self.input_ext = os.path.splitext(self.input_path)[1][1:]  # e.g. 'mp4'
        # Generate thumbnail
        thumb_path = os.path.join(self.project_dir, 'thumb.jpg')
        thumb_ok = thumbnailer.generate_thumbnail(self.input_path, thumb_path)
        if thumb_ok and os.path.exists(thumb_path):
            pix = QPixmap(thumb_path)
        else:
            pix = QPixmap(120, 90)
            pix.fill(Qt.GlobalColor.lightGray)
        self.thumbnail_label.setPixmap(pix)
        self.video_path_label.setText(f"<b>Project Video:</b> {self.input_path}")
        self.video_info_widget.show()
        self.chat_input.setDisabled(False)
        self.send_btn.setDisabled(False)
        self.dragdrop.text.setText(f"Loaded: {os.path.basename(file_path)}")
        self.chat_log.clear()
        self.append_chat_log("System", "Video loaded. Ready for commands.")

    def append_chat_log(self, sender, message):
        from datetime import datetime
        ts = datetime.now().strftime('%H:%M:%S')
        if sender == "User":
            self.chat_log.append(f'<div style="color:#005; text-align:right;"><b>User [{ts}]:</b> {message}</div>')
        elif sender == "System":
            self.chat_log.append(f'<div style="color:#333;"><b>System [{ts}]:</b> {message}</div>')
        elif sender == "Command":
            self.chat_log.append(f'<div style="font-family:monospace; color:#0a0;">{message}</div>')
        elif sender == "Error":
            self.chat_log.append(f'<div style="color:#a00;"><b>Error [{ts}]:</b> {message}</div>')
        self.chat_log.verticalScrollBar().setValue(self.chat_log.verticalScrollBar().maximum())

    def on_send_clicked(self):
        user_text = self.chat_input.toPlainText().strip()
        if not user_text:
            return
        self.append_chat_log("User", user_text)
        self.chat_input.clear()
        self.chat_input.setDisabled(True)
        self.send_btn.setDisabled(True)
        self.append_chat_log("System", "Processing...")
        # Run in background thread to keep UI responsive
        threading.Thread(target=self.process_command, args=(user_text,), daemon=True).start()

    def open_settings(self):
        dlg = SettingsDialog(self.app_config, self)
        dlg.settings_saved.connect(self.save_settings)
        dlg.exec()

    def save_settings(self, settings):
        self.app_config = settings
        config.save_config(settings)
        self.append_chat_log("System", "Settings updated.")

    def update_processed_video(self, video_path):
        thumb_path = os.path.join(self.project_dir, 'thumb.jpg')
        thumbnailer.generate_thumbnail(video_path, thumb_path)
        if os.path.exists(thumb_path):
            pix = QPixmap(thumb_path)
        else:
            pix = QPixmap(120, 90)
            pix.fill(Qt.GlobalColor.lightGray)
        self.processed_thumb.setPixmap(pix)
        self.processed_path.setText(f"<b>Processed Video:</b> {video_path}")
        self.processed_path_file = video_path
        self.processed_widget.show()

    def play_processed_video(self):
        if not self.processed_path_file or not os.path.exists(self.processed_path_file):
            return
        if sys.platform.startswith('darwin'):
            subprocess.call(['open', self.processed_path_file])
        elif os.name == 'nt':
            os.startfile(self.processed_path_file)
        elif os.name == 'posix':
            subprocess.call(['xdg-open', self.processed_path_file])

    def export_processed_video(self):
        if not self.processed_path_file or not os.path.exists(self.processed_path_file):
            return
        default_dir = self.app_config.get('export_dir', os.path.expanduser('~'))
        fname, _ = QFileDialog.getSaveFileName(self, "Export Processed Video", os.path.join(default_dir, os.path.basename(self.processed_path_file)))
        if fname:
            try:
                shutil.copy2(self.processed_path_file, fname)
                QMessageBox.information(self, "Export", f"Exported to {fname}")
            except Exception as e:
                QMessageBox.warning(self, "Export Failed", str(e))

    def process_command(self, user_text):
        # Use config values
        print(f"[INFO] User command: {user_text}")
        endpoint = self.app_config.get("llm_endpoint", "http://localhost:11434/api/generate")
        model = self.app_config.get("llm_model", "qwen3:lates")
        ffmpeg_path = self.app_config.get("ffmpeg_path", "ffmpeg")
        # Get FFmpeg command from LLM
        ffmpeg_cmd = llm_client.get_ffmpeg_command(user_text, self.input_ext, endpoint, model)
        if not ffmpeg_cmd:
            print("[ERROR] Failed to get command from LLM.")
            # Defer GUI update to main thread
            self.process_result_ready.emit({
                'error': 'Failed to get command from LLM.'
            })
            return
        print(f"[INFO] FFmpeg command from LLM: {ffmpeg_cmd}")
        # Validate
        valid, reason = ffmpeg_runner.validate_ffmpeg_command(ffmpeg_cmd)
        if not valid:
            print(f"[ERROR] Invalid FFmpeg command: {reason}")
            self.process_result_ready.emit({
                'error': f'Invalid FFmpeg command: {reason}',
                'ffmpeg_cmd': ffmpeg_cmd
            })
            return
        # Run FFmpeg (use ffmpeg_path if needed in ffmpeg_runner)
        print(f"[INFO] Running FFmpeg command...")
        result = ffmpeg_runner.run_ffmpeg_command(ffmpeg_cmd, self.project_dir)
        print(f"[INFO] FFmpeg finished. Success: {result['success']}")
        # Prepare result for main thread
        emit_data = {
            'ffmpeg_cmd': ffmpeg_cmd,
            'ffmpeg_result': result,
            'user_text': user_text
        }
        if not result['success']:
            emit_data['error'] = f"FFmpeg error: {result['stderr']}"
        self.process_result_ready.emit(emit_data)

    def on_process_result_ready(self, data):
        # This runs in the main thread. All GUI updates go here.
        user_text = data.get('user_text', None)
        ffmpeg_cmd = data.get('ffmpeg_cmd', None)
        ffmpeg_result = data.get('ffmpeg_result', None)
        error = data.get('error', None)
        if user_text:
            self.append_chat_log("User", user_text)
        if ffmpeg_cmd:
            self.append_chat_log("Command", ffmpeg_cmd)
        if error:
            self.append_chat_log("Error", error)
            self.enable_chat_input()
            return
        if ffmpeg_result and ffmpeg_result.get('success'):
            # Move output.ext to input.ext for chaining
            try:
                output_ext = os.path.splitext(ffmpeg_cmd.split('output.')[1].split()[0])[0]
                output_file = os.path.join(self.project_dir, f'output.{output_ext}')
                new_input_file = os.path.join(self.project_dir, f'input.{output_ext}')
                if not os.path.exists(output_file):
                    self.append_chat_log("Error", f"Expected output file {output_file} was not created. Check your command and try again.")
                    self.enable_chat_input()
                    return
                os.replace(output_file, new_input_file)
                self.input_path = new_input_file
                self.input_ext = output_ext
                # Generate new thumbnail
                thumb_path = os.path.join(self.project_dir, 'thumb.jpg')
                try:
                    thumbnailer.generate_thumbnail(self.input_path, thumb_path)
                    if os.path.exists(thumb_path):
                        pix = QPixmap(thumb_path)
                        self.thumbnail_label.setPixmap(pix)
                    else:
                        print(f"[WARN] Thumbnail not generated: {thumb_path}")
                        pix = QPixmap(120, 90)
                        pix.fill(Qt.GlobalColor.lightGray)
                        self.thumbnail_label.setPixmap(pix)
                except Exception as e:
                    print(f"[ERROR] Exception during thumbnail generation: {e}")
                self.video_path_label.setText(f"<b>Project Video:</b> {self.input_path}")
                # Update processed video area
                self.update_processed_video(self.input_path)
            except Exception as e:
                print(f"[ERROR] Could not update input file: {e}")
                self.append_chat_log("Error", f"Could not update input file: {e}")
            self.append_chat_log("System", "Success!")
        else:
            self.append_chat_log("Error", f"FFmpeg error: {ffmpeg_result.get('stderr') if ffmpeg_result else 'Unknown error'}")
        self.enable_chat_input()

    def enable_chat_input(self):
        self.chat_input.setDisabled(False)
        self.send_btn.setDisabled(False)

    def open_project_dialog(self):
        from PyQt6.QtWidgets import QDialog, QListWidget, QVBoxLayout, QPushButton
        import os
        dlg = QDialog(self)
        dlg.setWindowTitle("Reopen Project")
        layout = QVBoxLayout(dlg)
        list_widget = QListWidget()
        from backend import project_manager
        projects = project_manager.list_projects()
        for proj in projects:
            # Try to show video file name if exists
            files = os.listdir(proj)
            video_file = next((f for f in files if f.startswith('input.')), None)
            label = os.path.basename(proj)
            if video_file:
                label += f" - {video_file}"
            list_widget.addItem(label)
        layout.addWidget(list_widget)
        open_btn = QPushButton("Open")
        open_btn.setEnabled(False)
        layout.addWidget(open_btn)
        list_widget.currentRowChanged.connect(lambda idx: open_btn.setEnabled(idx >= 0))
        def do_open():
            idx = list_widget.currentRow()
            if idx < 0:
                return
            proj_dir = projects[idx]
            dlg.accept()
            self.load_project(proj_dir)
        open_btn.clicked.connect(do_open)
        dlg.setLayout(layout)
        dlg.exec()

    def load_project(self, proj_dir):
        import os
        # Find the input video file
        files = os.listdir(proj_dir)
        video_file = next((f for f in files if f.startswith('input.')), None)
        if not video_file:
            QMessageBox.warning(self, "Error", "No input video found in project.")
            return
        input_path = os.path.join(proj_dir, video_file)
        input_ext = os.path.splitext(input_path)[1][1:]
        thumb_path = os.path.join(proj_dir, 'thumb.jpg')
        # Set state
        self.project_dir = proj_dir
        self.input_path = input_path
        self.input_ext = input_ext
        # Update thumbnail
        if os.path.exists(thumb_path):
            pix = QPixmap(thumb_path)
        else:
            pix = QPixmap(120, 90)
            pix.fill(Qt.GlobalColor.lightGray)
        self.thumbnail_label.setPixmap(pix)
        self.video_path_label.setText(f"<b>Project Video:</b> {self.input_path}")
        self.video_info_widget.show()
        self.chat_input.setDisabled(False)
        self.send_btn.setDisabled(False)
        self.dragdrop.text.setText(f"Loaded: {os.path.basename(input_path)} (from project)")
        self.chat_log.clear()
        self.append_chat_log("System", "Project loaded. Ready for commands.") 