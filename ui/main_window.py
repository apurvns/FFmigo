from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QFileDialog, QLineEdit, QMessageBox, QSlider, QSizePolicy, QSplitter, QListWidget, QMenu, QListWidgetItem, QHBoxLayout, QScrollArea, QListWidgetItem, QStyledItemDelegate, QFrame
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
        self.new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
        self.help_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
        # Project header with edit and delete options
        self.project_header = QWidget()
        self.project_header_layout = QHBoxLayout(self.project_header)
        self.project_header_layout.setContentsMargins(0, 0, 0, 0)
        self.project_header_layout.setSpacing(12)
        self.project_header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)  # Center vertically
        
        # Project name (left-aligned)
        self.project_name_label = QLabel("FFMigo Video Editor")
        self.project_name_label.setStyleSheet("font-size: 32px; font-weight: 800; margin-bottom: 12px; letter-spacing: 0.5px; color: #e6eaf3;")
        self.project_name_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.project_header_layout.addWidget(self.project_name_label)
        
        # Edit button (pen icon)
        self.edit_project_btn = QPushButton()
        self.edit_project_btn.setObjectName("ProjectEditButton")
        self.edit_project_btn.setFixedSize(32, 32)
        self.edit_project_btn.setIconSize(QSize(20, 20))
        self.edit_project_btn.setToolTip("Edit project name")
        self.edit_project_btn.clicked.connect(self.edit_project_name)
        self.edit_project_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Set edit icon using inline SVG (like chat buttons)
        edit_svg_data = '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>'''
        edit_pixmap = QPixmap()
        edit_pixmap.loadFromData(bytes(edit_svg_data, encoding='utf-8'), "SVG")
        self.edit_project_btn.setIcon(QIcon(edit_pixmap))
        
        self.project_header_layout.addWidget(self.edit_project_btn)
        
        # Add stretch to push delete button to right
        self.project_header_layout.addStretch(1)
        
        # Delete button (right-aligned)
        self.delete_project_btn = QPushButton()
        self.delete_project_btn.setObjectName("ProjectDeleteButton")
        self.delete_project_btn.setFixedSize(32, 32)
        self.delete_project_btn.setIconSize(QSize(20, 20))
        self.delete_project_btn.setToolTip("Delete project")
        self.delete_project_btn.clicked.connect(self.delete_current_project)
        self.delete_project_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Set delete icon using inline SVG (like chat buttons)
        delete_svg_data = '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M3 6h18" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  <line x1="10" y1="11" x2="10" y2="17" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  <line x1="14" y1="11" x2="14" y2="17" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>'''
        delete_pixmap = QPixmap()
        delete_pixmap.loadFromData(bytes(delete_svg_data, encoding='utf-8'), "SVG")
        self.delete_project_btn.setIcon(QIcon(delete_pixmap))
        
        self.project_header_layout.addWidget(self.delete_project_btn)
        
        # Initially hide edit and delete buttons
        self.edit_project_btn.hide()
        self.delete_project_btn.hide()
        
        self.vbox.addWidget(self.project_header)
        # Drag-and-drop area
        self.dragdrop = DragDropWidget()
        self.dragdrop.file_dropped.connect(self.on_file_dropped)
        self.vbox.addWidget(self.dragdrop, stretch=7)
        # Main content area with adjustable splitter
        self.main_content_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_content_splitter.setHandleWidth(4)  # Increased handle width for better visual separation
        self.main_content_splitter.setChildrenCollapsible(True)
        
        # Left side: Video player area
        self.video_player_widget = QWidget()
        self.video_player_widget.setObjectName("VideoPlayerContainer")
        self.video_player_layout = QVBoxLayout(self.video_player_widget)
        self.video_player_layout.setContentsMargins(0, 0, 8, 0)  # Add right margin
        self.video_player_layout.setSpacing(8)
        
        # Video widget
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(400)
        self.video_widget.setObjectName("VideoWidget")
        self.video_player_layout.addWidget(self.video_widget, stretch=1)
        
        # Modern media control bar (simplified)
        self.media_controls = QWidget()
        self.media_controls.setObjectName("MediaControls")
        self.media_controls_layout = QHBoxLayout(self.media_controls)
        self.media_controls_layout.setContentsMargins(8, 8, 8, 8)
        self.media_controls_layout.setSpacing(8)

        # Bind Escape key to exit fullscreen
        self.esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self.video_widget)
        self.esc_shortcut.activated.connect(self.exitFullscreen)

        # Shortcut for Spacebar to toggle play/pause in fullscreen
        spacebar_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self.video_widget)
        spacebar_shortcut.activated.connect(self.spacebar_toggle_play_pause)
        
        # Play/Pause icon button
        self.play_pause_btn = QPushButton()
        self.play_pause_btn.setObjectName("PlayPauseButton")
        self.play_pause_btn.setIcon(QIcon.fromTheme("media-playback-start"))
        self.play_pause_btn.setFixedSize(40, 40)
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        self.play_pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
        self.fullscreen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.media_controls_layout.addWidget(self.fullscreen_btn)
        
        self.media_controls.hide()
        self.video_player_layout.addWidget(self.media_controls)
        
        # Right side: Terminal area
        self.terminal_widget = QWidget()
        self.terminal_widget.setObjectName("TerminalContainer")
        self.terminal_layout = QVBoxLayout(self.terminal_widget)
        self.terminal_layout.setContentsMargins(8, 0, 0, 0)  # Add left margin
        self.terminal_layout.setSpacing(8)
        
        # Chat log display (terminal)
        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setMinimumHeight(200)  # Reduced height
        self.chat_log.setObjectName("ChatLog")
        self.chat_log.setContentsMargins(0, 0, 0, 0)
        self.terminal_layout.addWidget(self.chat_log, stretch=1)
        
        # Add both widgets to the splitter
        self.main_content_splitter.addWidget(self.video_player_widget)
        self.main_content_splitter.addWidget(self.terminal_widget)
        
        # Set initial splitter proportions (60% video, 40% terminal)
        self.main_content_splitter.setSizes([700, 300])
        
        self.video_player_widget.hide()
        self.terminal_widget.hide()
        self.vbox.addWidget(self.main_content_splitter, stretch=1)
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
        
         # YouTube Download Section 
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
        
        # Chat input area - ChatGPT-style design
        self.chat_area = QWidget()
        self.chat_area.setObjectName("ChatInputArea")
        chat_layout = QVBoxLayout(self.chat_area)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(30)
        
        # Horizontal separator line
        self.action_separator = QFrame()
        self.action_separator.setFrameShape(QFrame.Shape.HLine)
        self.action_separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.action_separator.setObjectName("ActionSeparator")
        self.action_separator.setFixedHeight(4)
        self.action_separator.hide()  # Initially hidden
        
        # Action buttons row - will be positioned at bottom
        self.action_buttons = QWidget()
        self.action_buttons.setObjectName("ActionButtons")
        self.action_buttons_layout = QHBoxLayout(self.action_buttons)
        self.action_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.action_buttons_layout.setSpacing(5)
        
        # Checkpoint button (icon only)
        self.checkpoint_btn = QPushButton()
        self.checkpoint_btn.setObjectName("ActionButton")
        self.checkpoint_btn.setFixedSize(36, 36)
        self.checkpoint_btn.setToolTip("Checkpoints")
        self.checkpoint_btn.clicked.connect(self.open_checkpoints)
        self.checkpoint_btn.setEnabled(False)
        self.checkpoint_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # Set checkpoint icon
        checkpoint_svg_data = '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M9 12l2 2 4-4" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M21 12c0 4.97-4.03 9-9 9s-9-4.03-9-9 4.03-9 9-9 9 4.03 9 9z" stroke="white" stroke-width="2"/></svg>'''
        checkpoint_pixmap = QPixmap()
        checkpoint_pixmap.loadFromData(bytes(checkpoint_svg_data, encoding='utf-8'), "SVG")
        self.checkpoint_btn.setIcon(QIcon(checkpoint_pixmap))
        self.checkpoint_btn.setIconSize(QSize(20, 20))
        self.action_buttons_layout.addWidget(self.checkpoint_btn)
        
        # Undo button (icon only)
        self.undo_btn = QPushButton()
        self.undo_btn.setObjectName("ActionButton")
        self.undo_btn.setFixedSize(36, 36)
        self.undo_btn.setToolTip("Undo last command")
        self.undo_btn.clicked.connect(self.undo_last_command)
        self.undo_btn.setEnabled(False)
        self.undo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # Set undo icon
        undo_svg_data = '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M3 7v6h6" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'''
        undo_pixmap = QPixmap()
        undo_pixmap.loadFromData(bytes(undo_svg_data, encoding='utf-8'), "SVG")
        self.undo_btn.setIcon(QIcon(undo_pixmap))
        self.undo_btn.setIconSize(QSize(20, 20))
        self.action_buttons_layout.addWidget(self.undo_btn)
        
        # Export button (icon only)
        self.export_btn = QPushButton()
        self.export_btn.setObjectName("ActionButton")
        self.export_btn.setFixedSize(36, 36)
        self.export_btn.setToolTip("Export video")
        self.export_btn.clicked.connect(self.export_processed_video)
        self.export_btn.setEnabled(False)
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # Set export icon
        export_svg_data = '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><polyline points="7,10 12,15 17,10" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><line x1="12" y1="15" x2="12" y2="3" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'''
        export_pixmap = QPixmap()
        export_pixmap.loadFromData(bytes(export_svg_data, encoding='utf-8'), "SVG")
        self.export_btn.setIcon(QIcon(export_pixmap))
        self.export_btn.setIconSize(QSize(20, 20))
        self.action_buttons_layout.addWidget(self.export_btn)
        
        # Open Project Directory button (icon only)
        self.open_dir_btn = QPushButton()
        self.open_dir_btn.setObjectName("ActionButton")
        self.open_dir_btn.setFixedSize(36, 36)
        self.open_dir_btn.setToolTip("Open project directory")
        self.open_dir_btn.clicked.connect(self.open_project_directory)
        self.open_dir_btn.setEnabled(False)
        self.open_dir_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # Set folder icon
        folder_svg_data = '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'''
        folder_pixmap = QPixmap()
        folder_pixmap.loadFromData(bytes(folder_svg_data, encoding='utf-8'), "SVG")
        self.open_dir_btn.setIcon(QIcon(folder_pixmap))
        self.open_dir_btn.setIconSize(QSize(20, 20))
        self.action_buttons_layout.addWidget(self.open_dir_btn)
        
        self.action_buttons_layout.addStretch(1)  # Push buttons to the left
        self.action_buttons.hide()  # Initially hidden
        
        # Attachment chips bar (hidden when empty)
        self.attachment_bar = QWidget()
        self.attachment_bar.setObjectName("AttachmentBar")
        self.attachment_bar_layout = QHBoxLayout(self.attachment_bar)
        self.attachment_bar_layout.setContentsMargins(8, 4, 8, 4)  # Reduced padding
        self.attachment_bar_layout.setSpacing(2)  # Reduced spacing
        self.attachment_bar.hide()
        
        
        # Main input container with ChatGPT-style design
        input_container = QWidget()
        input_container.setObjectName("ChatInputContainer")
        input_layout = QVBoxLayout(input_container)  # Changed to VBoxLayout
        input_layout.setContentsMargins(8, 8, 8, 8)  # Back to original padding
        input_layout.setSpacing(8)  # Back to original spacing
        
        # Top: Text input area (full width)
        self.chat_input = QTextEdit()
        self.chat_input.setPlaceholderText("Type your video editing command here...")
        self.chat_input.setFixedHeight(24)  # Reduced height for max 3 lines
        self.chat_input.setDisabled(True)
        self.chat_input.setObjectName("ChatInput")
        self.chat_input.installEventFilter(self)
        self.chat_input.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.chat_input.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chat_input.textChanged.connect(self.on_chat_input_changed)
        input_layout.addWidget(self.chat_input)
        
        # Bottom: Button footer
        button_footer = QWidget()
        button_footer.setObjectName("ChatButtonFooter")
        button_layout = QHBoxLayout(button_footer)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(0)
        
        # Left: Attach button
        self.attach_btn = QPushButton("+")
        self.attach_btn.setObjectName("ChatAttachButton")
        self.attach_btn.setFixedSize(32, 32)
        self.attach_btn.setToolTip("Attach files")
        self.attach_btn.clicked.connect(self.on_attach_clicked)
        self.attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        button_layout.addWidget(self.attach_btn)
        
        # Spacer to push send button to the right
        button_layout.addStretch(1)
        
        # Right: Send button
        self.send_btn = QPushButton("↑")
        self.send_btn.setObjectName("ChatSendButton")
        self.send_btn.setFixedSize(32, 32)
        self.send_btn.setToolTip("Send message")
        self.send_btn.clicked.connect(self.on_send_clicked)
        self.send_btn.setEnabled(False)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        button_layout.addWidget(self.send_btn)
        
        input_layout.addWidget(button_footer)
        
        chat_layout.addWidget(self.action_separator)  # Add separator above action buttons
        chat_layout.addWidget(self.action_buttons)  # Add action buttons above chat input
        chat_layout.addWidget(self.attachment_bar)
        chat_layout.addWidget(input_container)
        self.vbox.addWidget(self.chat_area, stretch=0)
        
        # State
        self.project_dir = None
        self.input_path = None
        self.input_ext = None
        self.processed_path_file = None
        self.pending_attachments = []  # list of dicts: {name, type, abs_path, rel_path}
        self.input_video_analysis = None  # Cache for input video analysis
        self.process_result_ready.connect(self.on_process_result_ready)
        self.refresh_project_list()
        splitter.addWidget(self.main_area)  # <-- Ensure main area is visible
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        # Set initial UI state for no project
        self.set_ui_state_for_no_project()
        
        self.showMaximized()  # Start maximized, preferred for desktop apps

    def update_window_title(self):
        """Update the window title and heading based on current project"""
        if self.project_dir:
            project_name = project_manager.get_project_name(self.project_dir)
            self.setWindowTitle(f"FFMigo Video Editor - {project_name}")
            self.project_name_label.setText(f"{project_name}")
            # Show edit and delete buttons when project is loaded
            self.edit_project_btn.show()
            self.delete_project_btn.show()
        else:
            self.setWindowTitle("FFMigo Video Editor")
            self.project_name_label.setText("FFMigo Video Editor")
            # Hide edit and delete buttons when no project is loaded
            self.edit_project_btn.hide()
            self.delete_project_btn.hide()

    def on_file_dropped(self, file_path):
        # Create project dir and copy video
        self.project_dir = project_manager.create_project_dir()
        self.input_path = project_manager.copy_video_to_project(file_path, self.project_dir)
        self.input_ext = os.path.splitext(self.input_path)[1][1:]  # e.g. 'mp4'
        self.processed_path_file = self.input_path  # Set for export functionality
        
        # Initialize video analysis cache
        from backend import video_analyzer
        video_analyzer.init_cache(self.project_dir)
        
        # Analyze the input video on first load
        self.input_video_analysis = video_analyzer.analyze_video(self.input_path)
        if self.input_video_analysis:
            summary = video_analyzer.get_video_summary(self.input_video_analysis)
            print(f"[INFO] Input video analysis: {summary}")
        
        # Set UI state for project loaded
        self.set_ui_state_for_project_loaded()
        
        # Load video and update UI
        self.load_video(self.input_path)
        self.chat_log.clear()
        self.append_chat_log("System", "Video loaded. Ready for commands.")
        self.refresh_project_list(select=self.project_dir)
        self.update_window_title()

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
            # Terminal-style user input
            self.chat_log.append(f'<div class="UserBubble">$ {message}</div>')
        elif sender == "System":
            # Terminal-style system output
            self.chat_log.append(f'<div class="SystemBubble">[{ts}] {message}</div>')
        elif sender == "Command":
            # Terminal-style command output
            self.chat_log.append(f'<div class="CommandBubble">> {message}</div>')
        elif sender == "Error":
            # Terminal-style error output
            self.chat_log.append(f'<div class="ErrorBubble">ERROR: {message}</div>')
        self.chat_log.verticalScrollBar().setValue(self.chat_log.verticalScrollBar().maximum())

    def _make_attachment_chip(self, att, index):
        from PyQt6.QtWidgets import QWidget, QHBoxLayout
        chip = QWidget()
        chip.setObjectName("AttachmentChip")
        layout = QHBoxLayout(chip)
        layout.setContentsMargins(8, 4, 8, 4)  # Reduced padding
        layout.setSpacing(6)  # Reduced spacing
        
        # File type icon
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(16, 16)
        icon_lbl.setObjectName("AttachmentIcon")
        
        # Set appropriate icon based on file type
        file_type = att.get('type', 'file')
        if file_type == 'image':
            icon_lbl.setText("🖼️")
        elif file_type == 'video':
            icon_lbl.setText("🎬")
        elif file_type == 'audio':
            icon_lbl.setText("🎵")
        elif file_type == 'subtitle':
            icon_lbl.setText("📝")
        elif file_type == 'text':
            icon_lbl.setText("📄")
        else:
            icon_lbl.setText("📎")
        
        layout.addWidget(icon_lbl)
        
        # File name (truncated if too long)
        name_lbl = QLabel(att.get('name', ''))
        name_lbl.setToolTip(att.get('name', ''))
        name_lbl.setObjectName("AttachmentName")
        layout.addWidget(name_lbl)
        
        # Remove button
        remove_btn = QPushButton("×")
        remove_btn.setObjectName("AttachmentRemoveButton")
        remove_btn.setFixedSize(18, 18)
        remove_btn.setToolTip("Remove attachment")
        remove_btn.clicked.connect(lambda: self.remove_attachment(index))
        layout.addWidget(remove_btn)
        
        return chip

    def refresh_attachment_chips(self):
        # Clear existing
        while self.attachment_bar_layout.count():
            item = self.attachment_bar_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        # Rebuild
        if not self.pending_attachments:
            self.attachment_bar.hide()
            self.attach_btn.setProperty("active", False)
            self.attach_btn.style().unpolish(self.attach_btn)
            self.attach_btn.style().polish(self.attach_btn)
            return
        for idx, att in enumerate(self.pending_attachments):
            self.attachment_bar_layout.addWidget(self._make_attachment_chip(att, idx))
        self.attachment_bar.show()
        # Highlight attach button when attachments are present
        self.attach_btn.setProperty("active", True)
        self.attach_btn.style().unpolish(self.attach_btn)
        self.attach_btn.style().polish(self.attach_btn)

    def remove_attachment(self, index):
        try:
            if 0 <= index < len(self.pending_attachments):
                removed = self.pending_attachments.pop(index)
                print(f"[INFO] Removed attachment: {removed}")
                self.refresh_attachment_chips()
        except Exception as e:
            print(f"[WARNING] Failed to remove attachment at {index}: {e}")

    def on_attach_clicked(self):
        if not self.project_dir:
            QMessageBox.warning(self, "No Project", "Please load or create a project first.")
            return
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        dialog.setNameFilter("Supported Files (*.png *.jpg *.jpeg *.gif *.bmp *.svg *.webp *.mp4 *.mov *.avi *.mkv *.webm *.flv *.wmv *.mp3 *.wav *.aac *.flac *.txt *.srt *.ass *.vtt)")
        if dialog.exec():
            files = dialog.selectedFiles()
            for f in files:
                try:
                    rel_path, abs_path = project_manager.copy_asset_to_project(f, self.project_dir)
                    file_ext = os.path.splitext(f)[1].lower()
                    if file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp']:
                        file_type = 'image'
                    elif file_ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv']:
                        file_type = 'video'
                    elif file_ext in ['.mp3', '.wav', '.aac', '.flac']:
                        file_type = 'audio'
                    elif file_ext in ['.srt', '.ass', '.vtt']:
                        file_type = 'subtitle'
                    elif file_ext in ['.txt']:
                        file_type = 'text'
                    else:
                        file_type = 'file'
                    att = {
                        'name': os.path.basename(f),
                        'type': file_type,
                        'abs_path': abs_path,
                        'rel_path': rel_path,
                    }
                    self.pending_attachments.append(att)
                except Exception as e:
                    QMessageBox.warning(self, "Attachment Failed", f"Could not attach {os.path.basename(f)}: {e}")
            self.refresh_attachment_chips()

    def on_send_clicked(self):
        user_text = self.chat_input.toPlainText().strip()
        if not user_text:
            return
        # Only show user's message; attachments are visually represented as chips in the input bar
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

    def undo_last_command(self):
        """Undo the last command by restoring to the latest checkpoint"""
        if not self.project_dir:
            return
            
        # Get all checkpoints and find the latest one
        checkpoints = project_manager.list_checkpoints(self.project_dir)
        if not checkpoints:
            QMessageBox.information(self, "No Undo Available", "No checkpoints available to undo to.")
            return
        
        # Get the latest checkpoint (highest number)
        latest_checkpoint_num = checkpoints[-1][0]
        latest_meta = checkpoints[-1][1]
        
        # Show confirmation dialog
        reply = QMessageBox.question(
            self, 
            "Confirm Undo", 
            f"Are you sure you want to undo the last command?\n\nThis will restore to Checkpoint {latest_checkpoint_num}:\n'{latest_meta.get('user_command', 'Unknown operation')}'\n\nAll changes after this point will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Use the existing restore checkpoint logic
            success, result = project_manager.restore_checkpoint(self.project_dir, latest_checkpoint_num)
            
            if success:
                # Use the existing checkpoint restored handler
                self.on_checkpoint_restored(latest_checkpoint_num, result)
            else:
                QMessageBox.warning(self, "Undo Failed", f"Failed to undo: {result}")

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
        self.undo_btn.setEnabled(True)  # Enable undo after restoration
        
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
            self.open_dir_btn.setEnabled(True)  # Keep open directory enabled after processing
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
            
    def spacebar_toggle_play_pause(self):
        if self.video_widget.isFullScreen():
            self.toggle_play_pause()

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

    def exitFullscreen(self):
        if self.video_widget.isFullScreen():
            self.video_widget.setFullScreen(False)
        else:
            super().keyPressEvent(event)

    def handle_media_error(self, error):
        if error:
            QMessageBox.warning(self, "Playback Error", self.media_player.errorString())

    def open_project_directory(self):
        """Open the current project directory in the system file explorer"""
        if not self.project_dir:
            QMessageBox.warning(self, "No Project", "No project is currently loaded.")
            return
        
        try:
            import subprocess
            import platform
            
            if platform.system() == "Windows":
                subprocess.run(["explorer", self.project_dir])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", self.project_dir])
            else:  # Linux
                subprocess.run(["xdg-open", self.project_dir])
                
            print(f"[INFO] Opened project directory: {self.project_dir}")
        except Exception as e:
            print(f"[ERROR] Failed to open project directory: {e}")
            QMessageBox.warning(self, "Error", f"Could not open project directory: {e}")

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

    def process_command(self, user_text, retry_count=0):
        # Use config values
        print(f"[INFO] User command: {user_text} (retry #{retry_count})")
        provider = self.app_config.get("provider", "Ollama")
        endpoint = self.app_config.get("llm_endpoint", "http://localhost:11434/api/generate")
        model = self.app_config.get("llm_model", "llama3")
        api_key = self.app_config.get("api_key", None)
        ffmpeg_path = self.app_config.get("ffmpeg_path", "ffmpeg")
        
        # Create checkpoint before processing (only on first attempt)
        if retry_count == 0 and self.project_dir and self.input_path:
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
        
        # Build attachments payload (use rel paths for ffmpeg working dir)
        attachments_payload = []
        attachment_video_info = {}
        try:
            from backend import video_analyzer
            for a in self.pending_attachments:
                attachments_payload.append({
                    'name': a.get('name',''),
                    'type': a.get('type','file'),
                    'rel_path': a.get('rel_path','')
                })
                # Analyze attached video/audio files
                if a.get('type') in ['video', 'audio']:
                    analysis = video_analyzer.analyze_video(a.get('abs_path'))
                    if analysis:
                        summary = video_analyzer.get_video_summary(analysis)
                        attachment_video_info[a.get('rel_path')] = summary
                        print(f"[INFO] Attached {a.get('type')} analysis: {summary}")
        except Exception as e:
            print(f"[WARNING] Failed building attachments payload: {e}")
        
        # Prepare video analysis info for LLM
        input_video_info = None
        if self.input_video_analysis:
            from backend import video_analyzer
            input_video_info = video_analyzer.get_video_summary(self.input_video_analysis)
        
        # Get FFmpeg command from LLM
        try:
            import os
            input_filename = os.path.basename(self.input_path)
            print(f"[DEBUG] Using input file for FFmpeg command: {input_filename}")
            
            if hasattr(self, '_last_failed_command') and hasattr(self, '_last_error') and retry_count > 0:
                # This is a retry attempt - use retry function
                ffmpeg_cmd = llm_client.retry_ffmpeg_command(
                    self._last_failed_command,
                    self._last_error,
                    user_text,
                    input_filename,
                    self.input_ext,
                    endpoint,
                    model,
                    provider,
                    api_key,
                    attachments=attachments_payload,
                    input_video_info=input_video_info,
                    attachment_video_info=attachment_video_info if attachment_video_info else None
                )
            else:
                # First attempt - use normal function
                ffmpeg_cmd = llm_client.get_ffmpeg_command(
                    user_text,
                    input_filename,
                    self.input_ext,
                    endpoint,
                    model,
                    provider,
                    api_key,
                    attachments=attachments_payload,
                    input_video_info=input_video_info,
                    attachment_video_info=attachment_video_info if attachment_video_info else None
                )
        except Exception as e:
            print(f"[ERROR] Exception in get_ffmpeg_command: {e}")
            self.process_result_ready.emit({'error': f'LLM error: {e}'})
            return
        finally:
            # Clear attachments once the command has been generated/attempted (only on first try)
            if retry_count == 0:
                self.pending_attachments = []
                # Update chips UI on main thread
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, self.refresh_attachment_chips)
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
        emit_data = {'ffmpeg_cmd': ffmpeg_cmd, 'ffmpeg_result': result, 'user_text': user_text, 'retry_count': retry_count}
        if not result.get('success'):
            # Store failed command and error for potential retry
            self._last_failed_command = ffmpeg_cmd
            self._last_error = result.get('stderr', 'Unknown error')
            
            # Check if we should retry (max 2 retries to prevent infinite loops)
            if retry_count < 2:
                print(f"[INFO] FFmpeg failed, attempting retry #{retry_count + 1}")
                emit_data['retry_attempt'] = True
                self.process_result_ready.emit(emit_data)
                # Schedule retry in background thread
                threading.Thread(target=self.process_command, args=(user_text, retry_count + 1), daemon=True).start()
                return
            else:
                print(f"[ERROR] FFmpeg failed after {retry_count + 1} attempts, giving up")
                emit_data['error'] = f"FFmpeg error: {result.get('stderr')}"
        else:
            # Clear retry state on success
            if hasattr(self, '_last_failed_command'):
                delattr(self, '_last_failed_command')
            if hasattr(self, '_last_error'):
                delattr(self, '_last_error')
            # Move output.ext to a new unique input file for chaining (in background thread)
            try:
                import shutil
                # Extract output extension from command more reliably
                import re
                output_match = re.search(r'output\.([a-zA-Z0-9]+)', ffmpeg_cmd)
                if output_match:
                    output_ext = output_match.group(1)
                else:
                    output_ext = self.input_ext  # fallback to input extension
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
            retry_count = data.get('retry_count', 0)
            retry_attempt = data.get('retry_attempt', False)

            if ffmpeg_cmd:
                if retry_count > 0:
                    self.append_chat_log("Command", f"Retry #{retry_count}: {ffmpeg_cmd}")
                else:
                    self.append_chat_log("Command", ffmpeg_cmd)
                    
            if retry_attempt:
                # This is a retry notification - show user that we're retrying
                self.append_chat_log("System", f"Command failed, retrying with corrected command... (attempt {retry_count + 1}/3)")
                return  # Don't re-enable input yet, retry is in progress
                
            if error:
                if retry_count >= 2:
                    self.append_chat_log("Error", f"Failed after 3 attempts: {error}")
                else:
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
                if retry_count > 0:
                    self.append_chat_log("System", f"Success on retry #{retry_count}!")
                else:
                    self.append_chat_log("System", "Success!")
                # Enable undo button since a checkpoint was created
                self.undo_btn.setEnabled(True)
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
        self.on_chat_input_changed()

    def on_chat_input_changed(self):
        """Enable/disable send button based on whether there's text"""
        text = self.chat_input.toPlainText().strip()
        self.send_btn.setEnabled(bool(text) and not self.chat_input.isReadOnly())

    def refresh_project_list(self, select=None):
        from backend import project_manager
        projects = project_manager.list_projects()
        self.sidebar.set_projects(projects, selected=select or self.project_dir)

    def set_ui_state_for_no_project(self):
        """Set UI state when no project is loaded (app startup or new project)"""
        # Hide video-related components
        self.video_player_widget.hide()
        self.terminal_widget.hide()
        self.media_controls.hide()
        
        # Disable action buttons
        self.export_btn.setEnabled(False)
        self.open_dir_btn.setEnabled(False)
        self.checkpoint_btn.setEnabled(False)
        self.undo_btn.setEnabled(False)
        
        # Hide action UI elements
        self.action_separator.hide()
        self.action_buttons.hide()
        
        # Hide chat area and title
        self.chat_area.hide()
        self.project_name_label.hide()
        
        # Show drag and drop area
        self.dragdrop.show()

    def set_ui_state_for_project_loaded(self):
        """Set UI state when a project is loaded with video"""
        # Hide drag and drop area
        self.dragdrop.hide()
        
        # Show video-related components
        self.video_player_widget.show()
        self.terminal_widget.show()
        self.media_controls.show()
        
        # Enable action buttons
        self.export_btn.setEnabled(False)  # Will be enabled after processing
        self.open_dir_btn.setEnabled(True)
        self.checkpoint_btn.setEnabled(True)
        self.undo_btn.setEnabled(False)  # No checkpoints yet for undo
        
        # Show action UI elements
        self.action_separator.show()
        self.action_buttons.show()
        
        # Show chat area and title
        self.chat_area.show()
        self.project_name_label.show()
        
        # Enable chat input
        self.chat_input.setDisabled(False)

    def create_new_project(self):
        # Reset state and show drag-and-drop area for a new project
        self.project_dir = None
        self.input_path = None
        self.input_ext = None
        self.processed_path_file = None
        self.pending_attachments = [] # Clear attachments for new project
        self.input_video_analysis = None  # Clear video analysis
        
        # Set UI state for no project
        self.set_ui_state_for_no_project()
        
        # Clear chat and show message
        self.chat_log.clear()
        self.append_chat_log("System", "Create a new project by dragging and dropping a video file.")
        self.update_window_title()

    def rename_project(self, proj_dir):
        from PyQt6.QtWidgets import QInputDialog
        from backend import project_manager
        cur_name = project_manager.get_project_name(proj_dir)
        new_name, ok = QInputDialog.getText(self, "Rename Project", "New name:", text=cur_name)
        if ok and new_name and new_name != cur_name:
            project_manager.rename_project(proj_dir, new_name)
            self.refresh_project_list(select=proj_dir)
            # Update window title if this is the currently loaded project
            if self.project_dir == proj_dir:
                self.update_window_title()

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
                self.update_window_title()
            except Exception as e:
                QMessageBox.warning(self, "Delete Failed", f"Could not delete project: {e}")

    def edit_project_name(self):
        """Edit the name of the currently loaded project"""
        if self.project_dir:
            self.rename_project(self.project_dir)

    def delete_current_project(self):
        """Delete the currently loaded project"""
        if self.project_dir:
            self.delete_project(self.project_dir)

    def load_project(self, proj_dir):
        import os
        import subprocess
        import re
        
        print(f"[DEBUG] load_project: loading project from {proj_dir}")
        
        # Use shell command to find the latest input file
        try:
            files = os.listdir(proj_dir)
        
            # Filter files that match 'input_<number>.ext'
            input_files = [f for f in files if re.match(r'^input_\d+\.', f)]
            input_files.sort(key=lambda f: int(re.search(r'input_(\d+)', f).group(1)) if re.search(r'input_(\d+)', f) else 0)
            
            latest_input_file = input_files[-1] if input_files else None

            if not latest_input_file:
                fallback_files = [f for f in files if re.match(r'^input\..+$', f)]
                latest_input_file = fallback_files[0] if fallback_files else None

            if not latest_input_file:    
                QMessageBox.warning(self, "Error", "No input video found in project.")
                return

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
        
        # Initialize video analysis cache and analyze current input
        from backend import video_analyzer
        video_analyzer.init_cache(self.project_dir)
        self.input_video_analysis = video_analyzer.analyze_video(self.input_path)
        if self.input_video_analysis:
            summary = video_analyzer.get_video_summary(self.input_video_analysis)
            print(f"[INFO] Loaded project input video analysis: {summary}")
        
        # Set UI state for project loaded
        self.set_ui_state_for_project_loaded()
        
        # Load video
        self.load_video(self.input_path)
        
        # Enable export button if this is an edited video (has numbered files)
        has_edited_files = latest_input_file.startswith('input_')
        print(f"[DEBUG] load_project: has_edited_files: {has_edited_files}")
        self.export_btn.setEnabled(True)  # Always enable export button
        
        # Enable undo button if there are checkpoints available
        checkpoints = project_manager.list_checkpoints(self.project_dir)
        self.undo_btn.setEnabled(len(checkpoints) > 0)
        
        print(f"[DEBUG] load_project: export button state: {self.export_btn.isEnabled()}")
        
        # Clear chat and show message
        self.chat_log.clear()
        self.append_chat_log("System", "Project loaded. Ready for commands.")
        self.update_window_title()

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
