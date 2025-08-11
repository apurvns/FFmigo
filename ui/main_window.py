from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QFileDialog, QLineEdit, QMessageBox, QSlider, QSizePolicy, QSplitter, QListWidget, QMenu, QListWidgetItem, QHBoxLayout, QScrollArea, QListWidgetItem, QStyledItemDelegate
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QUrl, QTimer, QEvent, QSize, QPoint
from PyQt6.QtGui import QPixmap, QIcon, QDragEnterEvent, QDropEvent, QFont, QAction, QPainter, QColor
from PyQt6.QtWidgets import QStyle
import os
from backend import project_manager, thumbnailer
from ui.checkpoint_dialog import CheckpointDialog

class ProjectItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        # Get the project data
        project_dir = index.data(Qt.ItemDataRole.UserRole)
        if not project_dir:
            super().paint(painter, option, index)
            return
            
        from backend import project_manager
        name = project_manager.get_project_name(project_dir)
        
        # Truncate name if too long
        if len(name) > 18:
            name = name[:15] + "..."
        
        # Set up the painter
        painter.save()
        
        # Draw background if selected (use theme color #2d1e3a)
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor("#2d1e3a"))
        
        # Calculate text positions
        text_rect = option.rect.adjusted(12, 8, -40, -8)  # Leave space for ⋯ button
        button_rect = option.rect.adjusted(option.rect.width() - 30, 8, -8, -8)
        
        # Draw project name (left-aligned)
        painter.setPen(option.palette.text().color())
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)
        
        # Draw ⋯ button (right-aligned)
        painter.drawText(button_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "⋯")
        
        painter.restore()
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
    settings_requested = pyqtSignal()  # Add signal for settings
    help_requested = pyqtSignal()  # Add signal for help

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ProjectSidebar")
        self.setMinimumWidth(240)
        self.setMaximumWidth(320)
        self.setFixedWidth(300)  # Set a fixed width to prevent layout issues
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(0, 0, 0, 0)
        self.vbox.setSpacing(0)
        # Top row: New Project button centered + Settings button on right
        from PyQt6.QtWidgets import QHBoxLayout
        top_row = QHBoxLayout()
        top_row.setContentsMargins(12, 12, 12, 12)
        
        # Add stretch to push new button to center
        top_row.addStretch(1)
        
        self.new_btn = QPushButton("+ New Project")
        self.new_btn.setObjectName("NewProjectButton")
        self.new_btn.clicked.connect(self.new_project_requested.emit)
        top_row.addWidget(self.new_btn)
        
        # Add stretch to push settings button to right
        top_row.addStretch(1)
        
        self.settings_btn = QPushButton()
        self.settings_btn.setObjectName("SidebarSettingsButton")
        import os
        from PyQt6.QtGui import QIcon, QPixmap
        icon_path_svg = os.path.join(os.path.dirname(__file__), "resources/icons/settings.svg")
        icon_path_png = os.path.join(os.path.dirname(__file__), "resources/icons/settings.png")
        if os.path.exists(icon_path_svg):
            self.settings_btn.setIcon(QIcon(icon_path_svg))
        elif os.path.exists(icon_path_png):
            self.settings_btn.setIcon(QIcon(icon_path_png))
        else:
            svg_data = '''<svg width="20" height="20" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="14" cy="14" r="12" stroke="#a259ff" stroke-width="2" fill="#2d1e3a"/><path d="M14 10.5A3.5 3.5 0 1 1 10.5 14 3.5 3.5 0 0 1 14 10.5m0-2A5.5 5.5 0 1 0 19.5 14 5.5 5.5 0 0 0 14 8.5Z" fill="#fff"/><path d="M14 5v2M14 21v2M5 14h2M21 14h2M7.05 7.05l1.42 1.42M19.53 19.53l1.42 1.42M7.05 20.95l1.42-1.42M19.53 8.47l1.42-1.42" stroke="#a259ff" stroke-width="1.5" stroke-linecap="round"/></svg>'''
            pixmap = QPixmap()
            pixmap.loadFromData(bytes(svg_data, encoding='utf-8'), "SVG")
            self.settings_btn.setIcon(QIcon(pixmap))
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.setFixedSize(32, 32)
        self.settings_btn.setIconSize(QSize(20, 20))
        self.settings_btn.clicked.connect(self.settings_requested.emit)
        top_row.addWidget(self.settings_btn)
        
        # Help/Info button
        self.help_btn = QPushButton()
        self.help_btn.setObjectName("SidebarHelpButton")
        help_icon_path_svg = os.path.join(os.path.dirname(__file__), "resources/icons/help.svg")
        help_icon_path_png = os.path.join(os.path.dirname(__file__), "resources/icons/help.png")
        if os.path.exists(help_icon_path_svg):
            self.help_btn.setIcon(QIcon(help_icon_path_svg))
        elif os.path.exists(help_icon_path_png):
            self.help_btn.setIcon(QIcon(help_icon_path_png))
        else:
            # Fallback SVG icon for help - matches settings icon design
            help_svg_data = '''<svg width="20" height="20" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="14" cy="14" r="12" stroke="#a259ff" stroke-width="2" fill="#2d1e3a"/><path d="M14 8.5a5.5 5.5 0 0 1 5.5 5.5c0 3-2.5 4.5-2.5 4.5" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="14" cy="19.5" r="1" fill="#fff"/></svg>'''
            help_pixmap = QPixmap()
            help_pixmap.loadFromData(bytes(help_svg_data, encoding='utf-8'), "SVG")
            self.help_btn.setIcon(QIcon(help_pixmap))
        self.help_btn.setToolTip("About FFMigo")
        self.help_btn.setFixedSize(32, 32)
        self.help_btn.setIconSize(QSize(20, 20))
        self.help_btn.clicked.connect(self.help_requested.emit)
        top_row.addWidget(self.help_btn)
        
        self.vbox.addLayout(top_row)
        # Scrollable project list
        self.project_list = QListWidget()
        self.project_list.setObjectName("ProjectList")
        self.project_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.project_list.itemClicked.connect(self._on_item_clicked)
        # Context menu for renaming and deleting
        self.project_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.project_list.customContextMenuRequested.connect(self._show_context_menu)
        # Set custom delegate for proper ⋯ button alignment
        self.project_list.setItemDelegate(ProjectItemDelegate())
        # Wrap project_list in a QScrollArea
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setWidget(self.project_list)
        self.vbox.addWidget(self.scroll_area, stretch=1)
        # Remove old settings button at bottom
        # Add a container widget for bottom alignment
        # from PyQt6.QtWidgets import QWidget, QHBoxLayout
        # bottom_widget = QWidget()
        # bottom_layout = QHBoxLayout(bottom_widget)
        # bottom_layout.setContentsMargins(0, 8, 0, 8)
        # bottom_layout.addStretch(1)
        # bottom_layout.addWidget(self.settings_btn)
        # bottom_layout.addStretch(1)
        # self.vbox.addWidget(bottom_widget, alignment=Qt.AlignmentFlag.AlignBottom)
        self.setMinimumHeight(600)  # Ensure sidebar is tall enough

    def set_projects(self, projects, selected=None):
        self.project_list.clear()
        for proj in projects:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, proj)
            self.project_list.addItem(item)
            if selected and proj == selected:
                item.setSelected(True)

    def _on_item_clicked(self, item):
        proj_dir = item.data(Qt.ItemDataRole.UserRole)
        
        # Get click position to determine if menu button was clicked
        pos = self.project_list.mapFromGlobal(self.project_list.cursor().pos())
        item_rect = self.project_list.visualItemRect(item)
        
        # Check if click was in the right area (menu button area)
        menu_area = item_rect.right() - 30  # 30px from right edge for menu button
        if pos.x() > menu_area:
            # Menu button clicked - show context menu at click position
            self._show_context_menu_for_item_at_pos(item, pos)
        else:
            # Regular item click - select project
            self.project_selected.emit(proj_dir)

    def _show_context_menu(self, pos):
        item = self.project_list.itemAt(pos)
        if item:
            self._show_context_menu_for_item(item)

    def _show_context_menu_for_item(self, item):
        menu = QMenu(self)
        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")
        
        # Show menu at the right edge of the item, aligned with the menu button
        item_rect = self.project_list.visualItemRect(item)
        # Position menu at the right edge of the item
        menu_x = item_rect.right() - 5  # 5px from right edge
        menu_y = item_rect.center().y() - 10  # Center vertically with slight offset
        pos = self.project_list.mapToGlobal(QPoint(menu_x, menu_y))
        action = menu.exec(pos)
        
        if action == rename_action:
            proj_dir = item.data(Qt.ItemDataRole.UserRole)
            self.rename_project_requested.emit(proj_dir)
        elif action == delete_action:
            proj_dir = item.data(Qt.ItemDataRole.UserRole)
            self.delete_project_requested.emit(proj_dir)

    def _show_context_menu_for_item_at_pos(self, item, click_pos):
        menu = QMenu(self)
        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")
        
        # Use the actual click position for menu placement
        global_pos = self.project_list.mapToGlobal(click_pos)
        action = menu.exec(global_pos)
        
        if action == rename_action:
            proj_dir = item.data(Qt.ItemDataRole.UserRole)
            self.rename_project_requested.emit(proj_dir)
        elif action == delete_action:
            proj_dir = item.data(Qt.ItemDataRole.UserRole)
            self.delete_project_requested.emit(proj_dir)

class YouTubeDownloader(QThread):
    progress_signal = pyqtSignal(int)      # Progress in %
    finished_signal = pyqtSignal(str)      # File path when done
    error_signal = pyqtSignal(str)         # Error messages

    def __init__(self, url, project_dir):
        super().__init__()
        self.url = url
        self.project_dir = project_dir
        
    def run(self):
        try:
            

            ydl_opts = {
                'format': 'mp4',
                'outtmpl': os.path.join(self.project_dir, '%(title)s.%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'quiet': True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])

        except Exception as e:
            self.error_signal.emit(str(e))

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            percent_str = d.get('_percent_str', '0.0%').replace('%', '').strip()
            try:
                percent_val = int(float(percent_str))
                self.progress_signal.emit(percent_val)
            except:
                pass
        elif d['status'] == 'finished':
            self.finished_signal.emit(d['filename'])

class MainWindow(QMainWindow):
    process_result_ready = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("FFMigo Video Editor")
        self.resize(1100, 700)
        
        # Set application icon (only if not already set by main.py)
        if not self.windowIcon():
            icon_path = os.path.join(os.path.dirname(__file__), 'resources/icons/app_logo.svg')
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
            else:
                # Fallback to PNG if SVG doesn't exist
                png_icon_path = os.path.join(os.path.dirname(__file__), 'resources/icons/app_logo.png')
                if os.path.exists(png_icon_path):
                    self.setWindowIcon(QIcon(png_icon_path))
        
        self.setStyleSheet(open(os.path.join(os.path.dirname(__file__), '../style.qss')).read())
        self.setContentsMargins(0, 0, 0, 0)
        # Load config
        self.app_config = config.get_config()
        # Main layout: sidebar + main area
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        self.setCentralWidget(splitter)
        # Sidebar
        self.sidebar = ProjectSidebar()
        self.sidebar.project_selected.connect(self.load_project)
        self.sidebar.new_project_requested.connect(self.create_new_project)
        self.sidebar.rename_project_requested.connect(self.rename_project)
        self.sidebar.delete_project_requested.connect(self.delete_project)
        self.sidebar.settings_requested.connect(self.open_settings)  # Connect new signal
        self.sidebar.help_requested.connect(self.open_help)  # Connect help signal
        splitter.addWidget(self.sidebar)
        # Main area widget
        self.main_area = QWidget()
        self.vbox = QVBoxLayout(self.main_area)
        self.vbox.setContentsMargins(40, 32, 40, 32)  # Consistent margins for all main content
        self.vbox.setSpacing(24)
        # Large bold heading at the top center
        heading = QLabel("FFMigo Video Editor")
        heading.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        heading.setStyleSheet("font-size: 32px; font-weight: 800; margin-bottom: 12px; letter-spacing: 0.5px;")
        self.vbox.addWidget(heading)
        # Drag-and-drop area
        self.dragdrop = DragDropWidget()
        self.dragdrop.file_dropped.connect(self.on_file_dropped)
        self.vbox.addWidget(self.dragdrop, stretch=7)
        # Video player area (hidden until video loaded)
        self.video_player_widget = QWidget()
        self.video_player_layout = QVBoxLayout(self.video_player_widget)
        self.video_player_layout.setContentsMargins(0, 0, 0, 0)  # Remove extra margins
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
        # Checkpoint button
        self.checkpoint_btn = QPushButton("Checkpoints")
        self.checkpoint_btn.setObjectName("CheckpointButton")
        self.checkpoint_btn.setFixedHeight(36)
        self.checkpoint_btn.clicked.connect(self.open_checkpoints)
        self.checkpoint_btn.setEnabled(False)
        self.media_controls_layout.addWidget(self.checkpoint_btn)
        
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
        # --- YouTube Download Section ---
        youtube_layout = QHBoxLayout()
        self.youtube_input = QLineEdit()
        self.youtube_input.setPlaceholderText("Paste YouTube link here...")
        youtube_layout.addWidget(self.youtube_input)
        self.youtube_download_btn = QPushButton("Download")
        self.youtube_download_btn.clicked.connect(self.download_youtube_video)
        youtube_layout.addWidget(self.youtube_download_btn)
        self.youtube_progress = QProgressBar()
        self.youtube_progress.setValue(0)
        self.youtube_progress.hide()
        youtube_layout.addWidget(self.youtube_progress)
        youtube_widget = QWidget()
        youtube_widget.setLayout(youtube_layout)
        self.vbox.addWidget(youtube_widget)
        # Chat log display
        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setMinimumHeight(120)
        self.chat_log.setObjectName("ChatLog")
        self.chat_log.setContentsMargins(0, 0, 0, 0)  # Remove extra margins
        self.vbox.addWidget(self.chat_log, stretch=2)
        # Chat input area
        chat_area = QWidget()
        chat_layout = QHBoxLayout(chat_area)
        chat_layout.setContentsMargins(0, 0, 0, 0)  # Remove extra margins
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
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self.showMaximized()  # Start maximized, preferred for desktop apps

    def on_file_dropped(self, file_path):
        # Create project dir and copy video
        self.project_dir = project_manager.create_project_dir()
        self.input_path = project_manager.copy_video_to_project(file_path, self.project_dir)
        self.input_ext = os.path.splitext(self.input_path)[1][1:]  # e.g. 'mp4'
        self.processed_path_file = self.input_path  # Set for export functionality
        # Hide drag-and-drop, show video player
        self.dragdrop.hide()
        self.video_player_widget.show()
        self.load_video(self.input_path)
        self.media_controls.show()
        self.export_btn.setEnabled(False)
        self.checkpoint_btn.setEnabled(True)  # Enable checkpoints when video is loaded
        self.chat_input.setDisabled(False)
        self.chat_log.clear()
        self.append_chat_log("System", "Video loaded. Ready for commands.")
        self.refresh_project_list(select=self.project_dir)

    def download_youtube_video(self):
        url = self.youtube_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a YouTube link.")
            return
        self.youtube_progress.setFormat("Processing... ")
        self.youtube_progress.setValue(0)
        self.youtube_progress.show()

        project_name = f"YouTube_{int(time.time())}"  # Unique name
        project_dir = os.path.join(os.getcwd(), "projects", project_name)
        os.makedirs(project_dir, exist_ok=True)

        self.youtube_thread = YouTubeDownloader(url, project_dir)
        self.youtube_thread.progress_signal.connect(self.youtube_progress.setValue)
        self.youtube_thread.finished_signal.connect(self.youtube_download_finished)
        self.youtube_thread.error_signal.connect(self.youtube_download_error)
        self.youtube_thread.start()

    def youtube_download_finished(self, file_path):
        self.youtube_progress.hide()
        QMessageBox.information(self, "Download Complete", f"Video saved to project folder:\n{file_path}")
        self.load_project(os.path.dirname(file_path))  # Loads new project automatically


    def youtube_download_error(self, error_msg):
        self.youtube_progress.hide()
        QMessageBox.critical(self, "Download Failed", error_msg)
        
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

    def open_help(self):
        """Open the help/about dialog"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton
        
        dlg = QDialog(self)
        dlg.setWindowTitle("About FFMigo")
        dlg.setFixedSize(500, 400)
        dlg.setModal(True)
        
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)
        
        # App title and version
        title = QLabel("FFMigo Video Editor")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #a259ff; margin-bottom: 8px;")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)
        
        version = QLabel("Version 1.0")
        version.setStyleSheet("font-size: 14px; color: #888888; margin-bottom: 16px;")
        version.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(version)
        
        # Description
        desc = QLabel("AI-powered video editing with natural language commands. Transform your videos using simple text descriptions.")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 13px; line-height: 1.4; color: #666666; margin-bottom: 24px;")
        desc.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(desc)
        
        # Developer info
        dev_info = QLabel("Developed by Apurv")
        dev_info.setStyleSheet("font-size: 14px; font-weight: 600; color: #333333; margin-bottom: 8px;")
        dev_info.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(dev_info)
        
        # Links section
        links_layout = QHBoxLayout()
        links_layout.setSpacing(20)
        links_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        
        # Twitter link
        twitter_btn = QPushButton("🐦 Twitter")
        twitter_btn.setStyleSheet("""
            QPushButton {
                background-color: #1DA1F2;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1a8cd8;
            }
        """)
        twitter_btn.clicked.connect(lambda: self.open_url("https://twitter.com/apurvns"))
        links_layout.addWidget(twitter_btn)
        
        # GitHub link
        github_btn = QPushButton("📦 GitHub")
        github_btn.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        github_btn.clicked.connect(lambda: self.open_url("https://github.com/apurvns/ffmigo"))
        links_layout.addWidget(github_btn)
        
        # Contributors link
        contributors_btn = QPushButton("👥 Contributors")
        contributors_btn.setStyleSheet("""
            QPushButton {
                background-color: #6C757D;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        contributors_btn.clicked.connect(lambda: self.open_url("https://github.com/apurvns/ffmigo/graphs/contributors"))
        links_layout.addWidget(contributors_btn)
        
        layout.addLayout(links_layout)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #a259ff;
                color: white;
                border: none;
                padding: 10px 24px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #8a4fd8;
            }
        """)
        close_btn.clicked.connect(dlg.accept)
        close_btn.setFixedWidth(120)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)
        
        dlg.exec()

    def open_url(self, url):
        """Open URL in default browser"""
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl(url))

    def open_checkpoints(self):
        """Open the checkpoint dialog"""
        if not self.project_dir:
            QMessageBox.warning(self, "No Project", "No project is currently loaded.")
            return
        
        dlg = CheckpointDialog(self.project_dir, self)
        dlg.checkpoint_restored.connect(self.on_checkpoint_restored)
        dlg.exec()

    def on_checkpoint_restored(self, checkpoint_num, restored_file_path):
        """Handle checkpoint restoration"""
        print(f"[INFO] Checkpoint {checkpoint_num} restored to {restored_file_path}")
        print(f"[DEBUG] Before restoration - input_path: {self.input_path}")
        print(f"[DEBUG] Before restoration - input_ext: {self.input_ext}")
        print(f"[DEBUG] Restored file exists: {os.path.exists(restored_file_path)}")
        print(f"[DEBUG] Restored file size: {os.path.getsize(restored_file_path) if os.path.exists(restored_file_path) else 'N/A'}")
        
        # Use the restored file path directly
        self.input_path = restored_file_path
        self.input_ext = os.path.splitext(restored_file_path)[1][1:]
        
        print(f"[DEBUG] After restoration - input_path: {self.input_path}")
        print(f"[DEBUG] After restoration - input_ext: {self.input_ext}")
        print(f"[DEBUG] File exists: {os.path.exists(restored_file_path)}")
        
        # Force stop the current video player before loading the new one
        try:
            self.media_player.stop()
            print(f"[DEBUG] Stopped current media player")
        except:
            pass
        
        # Reload the video player with the restored file
        self.load_video(self.input_path)
        self.export_btn.setEnabled(True)
        self.checkpoint_btn.setEnabled(True)
        
        # Clear chat log and add restoration message
        self.chat_log.clear()
        self.append_chat_log("System", f"Restored to Checkpoint {checkpoint_num}. Ready for new commands.")
        
        print(f"[DEBUG] Restored to file: {restored_file_path}")
        print(f"[DEBUG] Video player should now show the restored checkpoint")

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
            self.checkpoint_btn.setEnabled(True)  # Enable checkpoints after processing
            self.processed_path_file = video_path  # Update for export functionality
            print(f'[DEBUG] update_processed_video: loaded {video_path} and updated controls')
            print(f'[DEBUG] update_processed_video: export button enabled: {self.export_btn.isEnabled()}')
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
        print("EXPORT BUTTON CLICKED!")
        print(f"[DEBUG] export_processed_video: input_path={self.input_path}")
        print(f"[DEBUG] export_processed_video: input_path exists={os.path.exists(self.input_path) if self.input_path else False}")
        print(f"[DEBUG] export_processed_video: export button enabled: {self.export_btn.isEnabled()}")
        
        if not self.input_path or not os.path.exists(self.input_path):
            print("EXPORT FAILED: No input path or file doesn't exist")
            QMessageBox.warning(self, "Export Failed", "No video to export.")
            return
        
        # Force enable the button just in case
        self.export_btn.setEnabled(True)
        
        default_dir = self.app_config.get('export_dir', os.path.expanduser('~'))
        suggested_name = os.path.basename(self.input_path)
        print(f"[DEBUG] export_processed_video: suggested_name={suggested_name}")
        
        fname, _ = QFileDialog.getSaveFileName(self, "Export Video", os.path.join(default_dir, suggested_name))
        print(f"[DEBUG] export_processed_video: selected fname={fname}")
        
        if fname:
            try:
                import shutil
                print(f"[DEBUG] export_processed_video: copying {self.input_path} to {fname}")
                shutil.copy2(self.input_path, fname)
                print("EXPORT SUCCESS!")
                QMessageBox.information(self, "Export", f"Exported to {fname}")
            except Exception as e:
                print(f"[ERROR] export_processed_video: exception: {e}")
                QMessageBox.warning(self, "Export Failed", str(e))
        else:
            print("EXPORT CANCELLED: User cancelled file dialog")

    def process_command(self, user_text):
        # Use config values
        print(f"[INFO] User command: {user_text}")
        provider = self.app_config.get("provider", "Ollama")
        endpoint = self.app_config.get("llm_endpoint", "http://localhost:11434/api/generate")
        model = self.app_config.get("llm_model", "llama3")
        api_key = self.app_config.get("api_key", None)
        ffmpeg_path = self.app_config.get("ffmpeg_path", "ffmpeg")
        
        # Create checkpoint before processing
        if self.project_dir and self.input_path:
            try:
                checkpoint_num = project_manager.create_checkpoint(
                    self.project_dir, 
                    self.input_path, 
                    f"Before: {user_text[:50]}{'...' if len(user_text) > 50 else ''}", 
                    user_text
                )
                print(f"[INFO] Created checkpoint {checkpoint_num} before processing")
            except Exception as e:
                print(f"[WARNING] Failed to create checkpoint: {e}")
        
        # Get FFmpeg command from LLM
        try:
            import os
            input_filename = os.path.basename(self.input_path)
            print(f"[DEBUG] Using input file for FFmpeg command: {input_filename}")
            ffmpeg_cmd = llm_client.get_ffmpeg_command(user_text, input_filename, self.input_ext, endpoint, model, provider, api_key)
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
        self.checkpoint_btn.setEnabled(False)  # Disable checkpoints for new project
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
        import subprocess
        
        print(f"[DEBUG] load_project: loading project from {proj_dir}")
        
        # Use shell command to find the latest input file
        try:
            # Find all input files and get the one with highest number
            cmd = f"ls {proj_dir}/input* 2>/dev/null | grep -E 'input_[0-9]+\.' | sort -V | tail -1"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            latest_input_file = result.stdout.strip()
            
            if not latest_input_file:
                # No numbered files found, try to find input.mp4
                cmd2 = f"ls {proj_dir}/input.mp4 2>/dev/null"
                result2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True)
                latest_input_file = result2.stdout.strip()
            
            if not latest_input_file:
                QMessageBox.warning(self, "Error", "No input video found in project.")
                return
            
            # Extract just the filename from the full path
            latest_input_file = os.path.basename(latest_input_file)
            print(f"[DEBUG] load_project: found latest file: {latest_input_file}")
            
        except Exception as e:
            print(f"[ERROR] load_project: error finding latest file: {e}")
            QMessageBox.warning(self, "Error", "No input video found in project.")
            return
        
        input_path = os.path.join(proj_dir, latest_input_file)
        input_ext = os.path.splitext(input_path)[1][1:]
        
        # Set state
        self.project_dir = proj_dir
        self.refresh_project_list(select=proj_dir)
        self.input_path = input_path
        self.input_ext = input_ext
        self.processed_path_file = input_path  # Update processed_path_file for export
        
        # Hide drag-and-drop, show video player
        self.dragdrop.hide()
        self.video_player_widget.show()
        self.load_video(self.input_path)
        self.media_controls.show()
        
        # Enable export button if this is an edited video (has numbered files)
        has_edited_files = latest_input_file.startswith('input_')
        print(f"[DEBUG] load_project: has_edited_files: {has_edited_files}")
        self.export_btn.setEnabled(True)  # Always enable export button
        self.checkpoint_btn.setEnabled(True)  # Enable checkpoints when project is loaded
        print(f"[DEBUG] load_project: export button state: {self.export_btn.isEnabled()}")
        
        self.chat_input.setDisabled(False)
        self.chat_log.clear()
        self.append_chat_log("System", "Project loaded. Ready for commands.") 

    def load_video(self, video_path):
        print(f'[DEBUG] load_video: called with {video_path}')
        print(f'[DEBUG] load_video: file exists = {os.path.exists(video_path)}')
        print(f'[DEBUG] load_video: file size = {os.path.getsize(video_path) if os.path.exists(video_path) else "N/A"}')
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
        print(f'[DEBUG] _create_and_load_player: file exists = {os.path.exists(video_path)}')
        try:
            from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
            url = QUrl.fromLocalFile(video_path)
            print(f'[DEBUG] _create_and_load_player: created QUrl from {video_path}')
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
            print(f'[DEBUG] _create_and_load_player: set new source to {video_path}')
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
