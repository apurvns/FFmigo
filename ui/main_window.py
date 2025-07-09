from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QFileDialog, QLineEdit, QMessageBox, QSlider, QSizePolicy, QSplitter, QListWidget, QMenu, QListWidgetItem, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QUrl, QTimer, QEvent, QSize
from PyQt6.QtGui import QPixmap, QIcon, QDragEnterEvent, QDropEvent, QFont, QAction
import os
from backend import project_manager, thumbnailer
from backend import llm_client, ffmpeg_runner
import threading
from ui.settings_dialog import SettingsDialog
from backend import config
import subprocess
import sys
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

class DragDropWidget(QWidget):
    file_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(300)
        self.setObjectName("DragDropArea")
        # Remove inline setStyleSheet, will be styled via QSS
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon = QLabel()
        # TODO: Replace with modern SVG icon in resources/icons/upload.svg
        # If not present, add your own SVG icon to resources/icons/upload.svg
        self.icon.setObjectName("DragDropIcon")
        self.icon.setPixmap(QPixmap(os.path.join(os.path.dirname(__file__), '../resources/icons/film.png')).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio))
        self.text = QLabel("<b>Drag and Drop Your Video File Here</b><br>or click to select a video")
        self.text.setObjectName("DragDropText")
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

class ProjectSidebar(QWidget):
    project_selected = pyqtSignal(str)
    new_project_requested = pyqtSignal()
    rename_project_requested = pyqtSignal(str)
    delete_project_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ProjectSidebar")
        self.setMinimumWidth(220)
        self.setMaximumWidth(320)
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(0, 0, 0, 0)
        self.vbox.setSpacing(0)
        # New project button at the top
        self.new_btn = QPushButton("+ New Project")
        self.new_btn.setObjectName("NewProjectButton")
        self.new_btn.clicked.connect(self.new_project_requested.emit)
        self.vbox.addWidget(self.new_btn)
        # Project list
        self.project_list = QListWidget()
        self.project_list.setObjectName("ProjectList")
        self.project_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.project_list.itemClicked.connect(self._on_item_clicked)
        self.vbox.addWidget(self.project_list, stretch=1)
        self.vbox.addStretch(1)
        # Context menu for renaming and deleting
        self.project_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.project_list.customContextMenuRequested.connect(self._show_context_menu)

    def set_projects(self, projects, selected=None):
        self.project_list.clear()
        from backend import project_manager
        for proj in projects:
            name = project_manager.get_project_name(proj)
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, proj)
            # Add delete icon
            item.setIcon(QIcon.fromTheme("edit-delete"))
            self.project_list.addItem(item)
            if selected and proj == selected:
                item.setSelected(True)

    def _on_item_clicked(self, item):
        proj_dir = item.data(Qt.ItemDataRole.UserRole)
        self.project_selected.emit(proj_dir)

    def _show_context_menu(self, pos):
        item = self.project_list.itemAt(pos)
        if item:
            menu = QMenu(self)
            rename_action = menu.addAction("Rename")
            delete_action = menu.addAction("Delete")
            action = menu.exec(self.project_list.mapToGlobal(pos))
            if action == rename_action:
                proj_dir = item.data(Qt.ItemDataRole.UserRole)
                self.rename_project_requested.emit(proj_dir)
            elif action == delete_action:
                proj_dir = item.data(Qt.ItemDataRole.UserRole)
                self.delete_project_requested.emit(proj_dir)

class MainWindow(QMainWindow):
    process_result_ready = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("FFMigo Video Editor")
        self.resize(1100, 700)
        # Load config
        self.app_config = config.get_config()
        # Main layout: sidebar + main area
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)
        # Sidebar
        self.sidebar = ProjectSidebar()
        self.sidebar.project_selected.connect(self.load_project)
        self.sidebar.new_project_requested.connect(self.create_new_project)
        self.sidebar.rename_project_requested.connect(self.rename_project)
        self.sidebar.delete_project_requested.connect(self.delete_project)
        splitter.addWidget(self.sidebar)
        # Main area widget
        self.main_area = QWidget()
        self.vbox = QVBoxLayout(self.main_area)
        # Settings button row
        settings_row = QHBoxLayout()
        settings_row.addStretch(1)
        settings_btn = QPushButton("Settings")
        settings_btn.setObjectName("SettingsButton")
        settings_btn.clicked.connect(self.open_settings)
        settings_row.addWidget(settings_btn)
        self.vbox.addLayout(settings_row)
        # Drag-and-drop area
        self.dragdrop = DragDropWidget()
        self.dragdrop.file_dropped.connect(self.on_file_dropped)
        self.vbox.addWidget(self.dragdrop, stretch=7)
        # Video player area (hidden until video loaded)
        self.video_player_widget = QWidget()
        self.video_player_layout = QVBoxLayout(self.video_player_widget)
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(360)
        self.video_player_layout.addWidget(self.video_widget)
        # Modern media control bar
        self.media_controls = QWidget()
        self.media_controls_layout = QHBoxLayout(self.media_controls)
        self.media_controls_layout.setContentsMargins(0, 0, 0, 0)
        # Play/Pause icon button
        self.play_pause_btn = QPushButton()
        self.play_pause_btn.setObjectName("PlayPauseButton")
        self.play_pause_btn.setIcon(QIcon.fromTheme("media-playback-start"))
        self.play_pause_btn.setFixedSize(40, 40)
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        self.media_controls_layout.addWidget(self.play_pause_btn)
        # Seek slider
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 100)
        self.seek_slider.setSingleStep(1)
        self.seek_slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.seek_slider.sliderMoved.connect(self.seek_position)
        self.media_controls_layout.addWidget(self.seek_slider)
        # Time label
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setObjectName("TimeLabel")
        self.media_controls_layout.addWidget(self.time_label)
        # Volume slider
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.media_controls_layout.addWidget(self.volume_slider)
        # Fullscreen button
        self.fullscreen_btn = QPushButton()
        self.fullscreen_btn.setObjectName("FullscreenButton")
        self.fullscreen_btn.setIcon(QIcon.fromTheme("view-fullscreen"))
        self.fullscreen_btn.setFixedSize(36, 36)
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        self.media_controls_layout.addWidget(self.fullscreen_btn)
        # Export button (only enabled after processing)
        self.export_btn = QPushButton("Export")
        self.export_btn.setObjectName("ExportButton")
        self.export_btn.setFixedHeight(36)
        self.export_btn.clicked.connect(self.export_processed_video)
        self.export_btn.setEnabled(False)
        self.media_controls_layout.addWidget(self.export_btn)
        self.media_controls.hide()
        self.video_player_layout.addWidget(self.media_controls)
        self.video_player_widget.hide()
        self.vbox.addWidget(self.video_player_widget, stretch=7)
        # Media player setup
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.playbackStateChanged.connect(self.update_play_pause_icon)
        self.media_player.positionChanged.connect(self.update_position)
        self.media_player.durationChanged.connect(self.update_duration)
        self.media_player.errorOccurred.connect(self.handle_media_error)
        # Timer for updating time label
        self.timer = QTimer()
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.update_time_label)
        # Chat log display
        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setMinimumHeight(120)
        self.chat_log.setObjectName("ChatLog")
        self.vbox.addWidget(self.chat_log, stretch=2)
        # Chat input area
        chat_area = QWidget()
        chat_layout = QHBoxLayout(chat_area)
        self.chat_input = QTextEdit()
        self.chat_input.setPlaceholderText("Type your video editing command here...")
        self.chat_input.setFixedHeight(60)
        self.chat_input.setDisabled(True)
        self.chat_input.setObjectName("ChatInput")
        self.chat_input.installEventFilter(self)
        chat_layout.addWidget(self.chat_input, stretch=1)
        self.vbox.addWidget(chat_area, stretch=3)
        # State
        self.project_dir = None
        self.input_path = None
        self.input_ext = None
        self.processed_path_file = None
        self.process_result_ready.connect(self.on_process_result_ready)
        self.refresh_project_list()
        splitter.addWidget(self.main_area)  # <-- Ensure main area is visible
        self.showMaximized()  # Start maximized, preferred for desktop apps

    def on_file_dropped(self, file_path):
        # Create project dir and copy video
        self.project_dir = project_manager.create_project_dir()
        self.input_path = project_manager.copy_video_to_project(file_path, self.project_dir)
        self.input_ext = os.path.splitext(self.input_path)[1][1:]  # e.g. 'mp4'
        # Hide drag-and-drop, show video player
        self.dragdrop.hide()
        self.video_player_widget.show()
        self.load_video(self.input_path)
        self.media_controls.show()
        self.export_btn.setEnabled(False)
        self.chat_input.setDisabled(False)
        self.chat_log.clear()
        self.append_chat_log("System", "Video loaded. Ready for commands.")
        self.refresh_project_list(select=self.project_dir)

    def append_chat_log(self, sender, message):
        from datetime import datetime
        ts = datetime.now().strftime('%H:%M:%S')
        if sender == "User":
            # Use objectName for QSS targeting
            self.chat_log.append(f'<div class="UserBubble"><b>User [{ts}]:</b> {message}</div>')
        elif sender == "System":
            self.chat_log.append(f'<div class="SystemBubble"><b>System [{ts}]:</b> {message}</div>')
        elif sender == "Command":
            self.chat_log.append(f'<div class="CommandBubble">{message}</div>')
        elif sender == "Error":
            self.chat_log.append(f'<div class="ErrorBubble"><b>Error [{ts}]:</b> {message}</div>')
        self.chat_log.verticalScrollBar().setValue(self.chat_log.verticalScrollBar().maximum())

    def on_send_clicked(self):
        user_text = self.chat_input.toPlainText().strip()
        if not user_text:
            return
        self.append_chat_log("User", user_text)
        self.chat_input.clear()
        self.chat_input.setDisabled(True)
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
        print(f'[DEBUG] Entered update_processed_video({video_path})')
        try:
            # Update the video player with the new processed video
            self.load_video(video_path)
            self.media_controls.show()
            self.export_btn.setEnabled(True)
            print(f'[DEBUG] update_processed_video: loaded {video_path} and updated controls')
        except Exception as e:
            print(f'[ERROR] Exception in update_processed_video: {e}')
            import traceback; traceback.print_exc()
            self.append_chat_log("Error", f"Exception updating video: {e}")

    def toggle_play_pause(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def update_play_pause_icon(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_pause_btn.setIcon(QIcon.fromTheme("media-playback-pause"))
        else:
            self.play_pause_btn.setIcon(QIcon.fromTheme("media-playback-start"))

    def update_position(self, position):
        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(position)
        self.seek_slider.blockSignals(False)
        self.update_time_label()

    def update_duration(self, duration):
        self.seek_slider.setRange(0, duration)
        self.update_time_label()

    def seek_position(self, position):
        self.media_player.setPosition(position)

    def set_volume(self, value):
        self.audio_output.setVolume(value / 100.0)

    def update_time_label(self):
        pos = self.media_player.position() // 1000
        dur = self.media_player.duration() // 1000
        pos_min, pos_sec = divmod(pos, 60)
        dur_min, dur_sec = divmod(dur, 60)
        self.time_label.setText(f"{pos_min:02}:{pos_sec:02} / {dur_min:02}:{dur_sec:02}")

    def toggle_fullscreen(self):
        if self.video_widget.isFullScreen():
            self.video_widget.setFullScreen(False)
        else:
            self.video_widget.setFullScreen(True)

    def handle_media_error(self, error):
        if error:
            QMessageBox.warning(self, "Playback Error", self.media_player.errorString())

    def export_processed_video(self):
        if not self.processed_path_file or not os.path.exists(self.processed_path_file):
            QMessageBox.warning(self, "Export Failed", "No processed video to export.")
            return
        default_dir = self.app_config.get('export_dir', os.path.expanduser('~'))
        fname, _ = QFileDialog.getSaveFileName(self, "Export Processed Video", os.path.join(default_dir, os.path.basename(self.processed_path_file)))
        if fname:
            try:
                import shutil
                shutil.copy2(self.processed_path_file, fname)
                QMessageBox.information(self, "Export", f"Exported to {fname}")
            except Exception as e:
                QMessageBox.warning(self, "Export Failed", str(e))

    def process_command(self, user_text):
        # Use config values
        print(f"[INFO] User command: {user_text}")
        endpoint = self.app_config.get("llm_endpoint", "http://localhost:11434/api/generate")
        model = self.app_config.get("llm_model", "deepseek-coder:6.7b")
        ffmpeg_path = self.app_config.get("ffmpeg_path", "ffmpeg")
        # Get FFmpeg command from LLM
        try:
            import os
            input_filename = os.path.basename(self.input_path)
            ffmpeg_cmd = llm_client.get_ffmpeg_command(user_text, input_filename, self.input_ext, endpoint, model)
        except Exception as e:
            print(f"[ERROR] Exception in get_ffmpeg_command: {e}")
            self.process_result_ready.emit({'error': f'LLM error: {e}'})
            return
        if not ffmpeg_cmd:
            print("[ERROR] Failed to get command from LLM.")
            self.process_result_ready.emit({'error': 'Failed to get command from LLM.'})
            return
        print(f"[INFO] FFmpeg command from LLM: {ffmpeg_cmd}")
        # Validate
        try:
            valid, reason = ffmpeg_runner.validate_ffmpeg_command(ffmpeg_cmd)
        except Exception as e:
            print(f"[ERROR] Exception in validate_ffmpeg_command: {e}")
            self.process_result_ready.emit({'error': f'Validation error: {e}', 'ffmpeg_cmd': ffmpeg_cmd})
            return
        if not valid:
            print(f"[ERROR] Invalid FFmpeg command: {reason}")
            self.process_result_ready.emit({'error': f'Invalid FFmpeg command: {reason}', 'ffmpeg_cmd': ffmpeg_cmd})
            return
        # Run FFmpeg (use ffmpeg_path if needed in ffmpeg_runner)
        print(f"[INFO] Running FFmpeg command...")
        try:
            result = ffmpeg_runner.run_ffmpeg_command(ffmpeg_cmd, self.project_dir)
        except Exception as e:
            print(f"[ERROR] Exception in run_ffmpeg_command: {e}")
            self.process_result_ready.emit({'error': f'FFmpeg run error: {e}', 'ffmpeg_cmd': ffmpeg_cmd})
            return
        print(f"[INFO] FFmpeg finished. Success: {result.get('success')}")
        emit_data = {'ffmpeg_cmd': ffmpeg_cmd, 'ffmpeg_result': result, 'user_text': user_text}
        if not result.get('success'):
            emit_data['error'] = f"FFmpeg error: {result.get('stderr')}"
        else:
            # Move output.ext to a new unique input file for chaining (in background thread)
            try:
                import shutil
                output_ext = os.path.splitext(ffmpeg_cmd.split('output.')[1].split()[0])[0]
                output_file = os.path.join(self.project_dir, f'output.{output_ext}')
                print(f"[DEBUG] Looking for output file: {output_file}")
                if not os.path.exists(output_file):
                    print(f"[ERROR] Output file not found: {output_file}")
                    emit_data['error'] = f"Expected output file {output_file} was not created. Check your command and try again."
                    self.process_result_ready.emit(emit_data)
                    return
                base = os.path.join(self.project_dir, f'input')
                idx = 1
                max_idx = 1000
                found_unique = False
                while idx <= max_idx:
                    new_input_file = f"{base}_{idx}.{output_ext}"
                    if not os.path.exists(new_input_file):
                        found_unique = True
                        break
                    idx += 1
                if not found_unique:
                    print(f"[ERROR] Could not find unique filename after {max_idx} tries.")
                    emit_data['error'] = f"Could not find unique filename after {max_idx} tries."
                    self.process_result_ready.emit(emit_data)
                    return
                print(f"[DEBUG] Moving {output_file} to {new_input_file}")
                shutil.move(output_file, new_input_file)
                thumb_path = os.path.join(self.project_dir, 'thumb.jpg')
                try:
                    thumbnailer.generate_thumbnail(new_input_file, thumb_path)
                except Exception as e:
                    print(f"[ERROR] Exception during thumbnail generation: {e}")
                emit_data['new_input_file'] = new_input_file
                emit_data['new_input_ext'] = output_ext
            except Exception as e:
                print(f"[ERROR] Could not update input file: {e}")
                emit_data['error'] = f"Could not update input file: {e}"
                self.process_result_ready.emit(emit_data)
                return
        self.process_result_ready.emit(emit_data)

    def on_process_result_ready(self, data):
        print('[DEBUG] Entered on_process_result_ready')
        try:
            user_text = data.get('user_text', None)
            ffmpeg_cmd = data.get('ffmpeg_cmd', None)
            ffmpeg_result = data.get('ffmpeg_result', None)
            error = data.get('error', None)
            new_input_file = data.get('new_input_file', None)
            new_input_ext = data.get('new_input_ext', None)
            if user_text:
                self.append_chat_log("User", user_text)
            if ffmpeg_cmd:
                self.append_chat_log("Command", ffmpeg_cmd)
            if error:
                self.append_chat_log("Error", error)
                self.enable_chat_input()
                print('[DEBUG] on_process_result_ready: error branch, returning')
                return
            if ffmpeg_result and ffmpeg_result.get('success'):
                if new_input_file and new_input_ext:
                    print(f'[DEBUG] on_process_result_ready: calling update_processed_video({new_input_file})')
                    self.input_path = new_input_file
                    self.input_ext = new_input_ext
                    self.update_processed_video(self.input_path)
                self.append_chat_log("System", "Success!")
            else:
                self.append_chat_log("Error", f"FFmpeg error: {ffmpeg_result.get('stderr') if ffmpeg_result else 'Unknown error'}")
            self.enable_chat_input()
            print('[DEBUG] Exiting on_process_result_ready')
        except Exception as e:
            print(f'[ERROR] Exception in on_process_result_ready: {e}')
            import traceback; traceback.print_exc()
            self.append_chat_log("Error", f"Exception in result handler: {e}")
            self.enable_chat_input()

    def enable_chat_input(self):
        self.chat_input.setDisabled(False)

    def refresh_project_list(self, select=None):
        from backend import project_manager
        projects = project_manager.list_projects()
        self.sidebar.set_projects(projects, selected=select or self.project_dir)

    def create_new_project(self):
        # Reset state and show drag-and-drop area for a new project
        self.project_dir = None
        self.input_path = None
        self.input_ext = None
        self.processed_path_file = None
        self.dragdrop.show()
        self.video_player_widget.hide()
        self.media_controls.hide()
        self.export_btn.setEnabled(False)
        self.chat_input.setDisabled(False)
        self.chat_log.clear()
        self.append_chat_log("System", "Create a new project by dragging and dropping a video file.")

    def rename_project(self, proj_dir):
        from PyQt6.QtWidgets import QInputDialog
        from backend import project_manager
        cur_name = project_manager.get_project_name(proj_dir)
        new_name, ok = QInputDialog.getText(self, "Rename Project", "New name:", text=cur_name)
        if ok and new_name and new_name != cur_name:
            project_manager.rename_project(proj_dir, new_name)
            self.refresh_project_list(select=proj_dir)

    def delete_project(self, proj_dir):
        from PyQt6.QtWidgets import QMessageBox
        from backend import project_manager
        reply = QMessageBox.question(self, "Delete Project", f"Are you sure you want to delete this project? This cannot be undone.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            import shutil
            try:
                shutil.rmtree(proj_dir)
                # If the deleted project is currently loaded, reset to new project
                if self.project_dir == proj_dir:
                    self.create_new_project()
                self.refresh_project_list()
            except Exception as e:
                QMessageBox.warning(self, "Delete Failed", f"Could not delete project: {e}")

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
        # Set state
        self.project_dir = proj_dir
        self.refresh_project_list(select=proj_dir)
        self.input_path = input_path
        self.input_ext = input_ext
        # Hide drag-and-drop, show video player
        self.dragdrop.hide()
        self.video_player_widget.show()
        self.load_video(self.input_path)
        self.media_controls.show()
        self.export_btn.setEnabled(False)
        self.chat_input.setDisabled(False)
        self.chat_log.clear()
        self.append_chat_log("System", "Project loaded. Ready for commands.") 

    def load_video(self, video_path):
        print(f'[DEBUG] load_video: called with {video_path}')
        try:
            url = QUrl.fromLocalFile(video_path)
            print('[DEBUG] load_video: created QUrl')
            # Stop and delete the media player and audio output
            try:
                self.media_player.stop()
                print('[DEBUG] load_video: stopped old media_player')
                self.media_player.setSource(QUrl())
                print('[DEBUG] load_video: cleared old source')
                del self.media_player
                del self.audio_output
                print('[DEBUG] load_video: deleted old media_player and audio_output')
            except Exception as e:
                print(f'[DEBUG] load_video: exception deleting old player: {e}')
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._create_and_load_player(video_path))
            print('[DEBUG] load_video: scheduled _create_and_load_player')
        except Exception as e:
            print(f'[ERROR] Exception in load_video: {e}')
            import traceback; traceback.print_exc()
            self.append_chat_log("Error", f"Exception loading video: {e}")
            return

    def _create_and_load_player(self, video_path):
        print(f'[DEBUG] _create_and_load_player: called with {video_path}')
        try:
            from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
            url = QUrl.fromLocalFile(video_path)
            self.media_player = QMediaPlayer()
            print('[DEBUG] _create_and_load_player: created new QMediaPlayer')
            self.audio_output = QAudioOutput()
            print('[DEBUG] _create_and_load_player: created new QAudioOutput')
            self.media_player.setVideoOutput(self.video_widget)
            print('[DEBUG] _create_and_load_player: set video output')
            self.media_player.setAudioOutput(self.audio_output)
            print('[DEBUG] _create_and_load_player: set audio output')
            self.media_player.playbackStateChanged.connect(self.update_play_pause_icon)
            self.media_player.positionChanged.connect(self.update_position)
            self.media_player.durationChanged.connect(self.update_duration)
            self.media_player.errorOccurred.connect(self.handle_media_error)
            print('[DEBUG] _create_and_load_player: connected signals')
            self.media_player.setSource(url)
            print('[DEBUG] _create_and_load_player: set new source')
            self.media_player.pause()
            print('[DEBUG] _create_and_load_player: paused player')
            self.processed_path_file = video_path
            self.seek_slider.setValue(0)
            self.seek_slider.setRange(0, 0)
            self.time_label.setText("00:00 / 00:00")
            print('[DEBUG] _create_and_load_player: finished')
        except Exception as e:
            print(f'[ERROR] Exception in _create_and_load_player: {e}')
            import traceback; traceback.print_exc()
            self.append_chat_log("Error", f"Exception loading video: {e}")
            return

    def eventFilter(self, obj, event):
        if obj == self.chat_input and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    return False  # allow newline
                else:
                    self.on_send_clicked()
                    return True  # block default
        return super().eventFilter(obj, event) 