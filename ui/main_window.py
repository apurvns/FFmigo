from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QFileDialog, QLineEdit, QMessageBox, QSlider, QSizePolicy, QSplitter, QListWidget, QMenu, QListWidgetItem, QHBoxLayout, QScrollArea, QListWidgetItem, QStyledItemDelegate, QFrame, QStackedWidget
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QUrl, QTimer, QEvent, QSize, QPoint
from PyQt6.QtGui import QPixmap, QIcon, QDragEnterEvent, QDropEvent, QFont, QAction, QPainter, QColor
from PyQt6.QtWidgets import QStyle
from PyQt6.QtGui import QShortcut, QKeySequence
import os
import time
from PyQt6.QtWidgets import QPushButton, QLineEdit, QProgressBar
from PyQt6.QtCore import pyqtSignal,QThread
import yt_dlp
import threading
from backend import project_manager, thumbnailer, video_analyzer
from ui.checkpoint_dialog import CheckpointDialog
from backend.icon_utils import load_app_icon
from backend import llm_client, ffmpeg_runner
import threading
from ui.settings_dialog import SettingsDialog
from backend import config
from backend.theme import render_stylesheet
from PyQt6.QtWidgets import QApplication
import subprocess
import sys
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

class ProjectItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        # Get the project data
        project_dir = index.data(Qt.ItemDataRole.UserRole)
        if not project_dir:
            super().paint(painter, option, index)
            return
            
        name = project_manager.get_project_name(project_dir)
        
        # Truncate name if too long
        if len(name) > 18:
            name = name[:15] + "..."
        
        # Set up the painter
        painter.save()
        
        # Draw background if selected (use centralized theme color)
        if option.state & QStyle.StateFlag.State_Selected:
            from backend.theme import get_theme_color
            selected_color = get_theme_color('selected_bg')
            painter.fillRect(option.rect, QColor(selected_color))
        
        # Calculate text positions
        text_rect = option.rect.adjusted(12, 8, -40, -8)  # Leave space for ⋯ button
        button_rect = option.rect.adjusted(option.rect.width() - 30, 8, -8, -8)
        
        # Draw project name (left-aligned)
        painter.setPen(option.palette.text().color())
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)
        
        # Draw ⋯ button (right-aligned)
        painter.drawText(button_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "⋯")
        
        painter.restore()

class DragDropWidget(QWidget):
    files_dropped = pyqtSignal(list)  # Changed to emit list of files

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
        self.text = QLabel("<b>Drag and Drop Your Video Files Here</b><br>or click to select videos (multiple selection supported)")
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
            file_paths = [url.toLocalFile() for url in urls]
            # Filter for video files only
            video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'}
            video_files = [path for path in file_paths if os.path.splitext(path)[1].lower() in video_extensions]
            if video_files:
                self.files_dropped.emit(video_files)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            file_dialog = QFileDialog(self)
            file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)  # Changed to multiple selection
            file_dialog.setNameFilter("Video Files (*.mp4 *.mov *.avi *.mkv *.webm *.flv *.wmv)")
            if file_dialog.exec():
                selected = file_dialog.selectedFiles()
                if selected:
                    self.files_dropped.emit(selected)





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
        
        # Top row: Logo + New Project button + Settings + Help buttons (all in one row)
        from PyQt6.QtWidgets import QHBoxLayout
        import os
        from PyQt6.QtGui import QPixmap, QIcon
        top_row = QHBoxLayout()
        top_row.setContentsMargins(12, 12, 12, 12)
        top_row.setSpacing(4)
        
        # App logo (left)
        self.app_logo_label = QLabel()
        self.app_logo_label.setFixedSize(120, 32)
        self.app_logo_label.setScaledContents(True)
        self.app_logo_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # Load app logo based on current theme
        from backend import config
        cfg = config.get_config()
        current_theme = cfg.get('theme', 'dark')
        
        if current_theme == 'light':
            logo_filename = "app_in_logo_light.png"
        else:
            logo_filename = "app_in_logo.png"
            
        logo_path = os.path.join(os.path.dirname(__file__), "resources/icons", logo_filename)
        if os.path.exists(logo_path):
            logo_pixmap = QPixmap(logo_path)
            if not logo_pixmap.isNull():
                self.app_logo_label.setPixmap(logo_pixmap.scaled(120, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
        top_row.addWidget(self.app_logo_label)
        
        # Add stretch to push all buttons to right
        top_row.addStretch(1)
        
        # New Project button (right)
        self.new_btn = QPushButton()
        self.new_btn.setObjectName("SidebarNewProjectButton")
        # Icon will be set by _update_all_button_icons()
        self.new_btn.setToolTip("New Project")
        self.new_btn.setFixedSize(32, 32)
        self.new_btn.setIconSize(QSize(26, 26))
        self.new_btn.clicked.connect(self.new_project_requested.emit)
        self.new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        top_row.addWidget(self.new_btn)
        
        # Settings button (right)
        self.settings_btn = QPushButton()
        self.settings_btn.setObjectName("SidebarSettingsButton")
        # Icon will be set by _update_all_button_icons()
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.setFixedSize(32, 32)
        self.settings_btn.setIconSize(QSize(26, 26))
        self.settings_btn.clicked.connect(self.settings_requested.emit)
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        top_row.addWidget(self.settings_btn)
        
        # Theme toggle button (right, placed before Help)
        self.theme_btn = QPushButton()
        # Reuse existing style for sidebar buttons without editing QSS
        self.theme_btn.setObjectName("SidebarSettingsButton")
        # Icon will be set by _update_all_button_icons()
        self.theme_btn.setToolTip("Toggle Theme")
        self.theme_btn.setFixedSize(32, 32)
        self.theme_btn.setIconSize(QSize(26, 26))
        self.theme_btn.clicked.connect(self._toggle_theme)
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        top_row.addWidget(self.theme_btn)

        # Help/Info button (right)
        self.help_btn = QPushButton()
        self.help_btn.setObjectName("SidebarHelpButton")
        # Icon will be set by _update_all_button_icons()
        self.help_btn.setToolTip("About FFMigo")
        self.help_btn.setFixedSize(32, 32)
        self.help_btn.setIconSize(QSize(26, 26))
        self.help_btn.clicked.connect(self.help_requested.emit)
        self.help_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.help_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
        
        # Initialize button icons
        self._initialize_sidebar_button_icons()

    def _initialize_sidebar_button_icons(self):
        """Initialize sidebar button icons using dynamic icon loading"""
        from backend.icon_loader import get_icon
        
        # Set icons for all sidebar buttons
        if hasattr(self, 'new_btn'):
            self.new_btn.setIcon(get_icon("new_project", 26))
        if hasattr(self, 'settings_btn'):
            self.settings_btn.setIcon(get_icon("settings", 26))
        if hasattr(self, 'help_btn'):
            self.help_btn.setIcon(get_icon("help", 26))
        if hasattr(self, 'theme_btn'):
            self._update_theme_button_icon()

    def _update_theme_button_icon(self):
        # Get theme from parent MainWindow
        main_window = self.parent()
        while main_window and not isinstance(main_window, MainWindow):
            main_window = main_window.parent()
        
        if main_window and hasattr(main_window, '_current_theme'):
            theme = main_window._current_theme()
        else:
            theme = 'dark'  # fallback
            
        # Use sun icon when in dark mode (indicates switch to light), moon in light mode
        from backend.icon_loader import get_icon
        if theme == 'dark':
            # Sun icon - indicates switch to light theme
            self.theme_btn.setIcon(get_icon("sun", 26))
        else:
            # Moon icon - indicates switch to dark theme
            self.theme_btn.setIcon(get_icon("moon", 26))

    def _update_app_logo(self):
        """Update app logo based on current theme"""
        from backend import config
        cfg = config.get_config()
        current_theme = cfg.get('theme', 'dark')
        
        if current_theme == 'light':
            logo_filename = "app_in_logo_light.png"
        else:
            logo_filename = "app_in_logo.png"
            
        logo_path = os.path.join(os.path.dirname(__file__), "resources/icons", logo_filename)
        if os.path.exists(logo_path):
            logo_pixmap = QPixmap(logo_path)
            if not logo_pixmap.isNull():
                self.app_logo_label.setPixmap(logo_pixmap.scaled(120, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))


    def _toggle_theme(self):
        # Flip theme in config
        cfg = config.get_config()
        current = cfg.get('theme', 'dark')
        new_theme = 'light' if current == 'dark' else 'dark'
        cfg['theme'] = new_theme
        try:
            config.save_config(cfg)
        except Exception as e:
            print(f"Warning: could not save theme setting: {e}")

        # Reapply stylesheet using backend.theme renderer
        try:
            base_dir = os.path.dirname(os.path.dirname(__file__))  # project root
            qss_path = os.path.join(base_dir, 'style.qss')
            with open(qss_path, 'r', encoding='utf-8') as f:
                qss_text = f.read()
            
            # Apply theme to stylesheet
            rendered = render_stylesheet(qss_text, new_theme)
            
            app = QApplication.instance()
            if app is not None:
                # Clear current stylesheet first to force refresh
                app.setStyleSheet("")
                app.setStyleSheet(rendered)
                
                # Clear icon cache and update all button icons
                from backend.icon_loader import clear_icon_cache
                clear_icon_cache()
                app.processEvents()
        except Exception as e:
            print(f"Warning: could not reapply stylesheet: {e}")
            import traceback
            traceback.print_exc()

        # Update button icon to reflect new theme
        self._update_theme_button_icon()
        # Update app logo to reflect new theme
        self._update_app_logo()
        # Update all button icons to match new theme
        main_window = self.parent()
        while main_window and not isinstance(main_window, MainWindow):
            main_window = main_window.parent()
        
        if main_window and hasattr(main_window, '_update_all_button_icons'):
            main_window._update_all_button_icons()

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
        self._finished = False  # Flag to prevent multiple finish signals
        
    def run(self):
        try:
            ydl_opts = {
                'format': 'best',
                'outtmpl': os.path.join(self.project_dir, '%(title)s.%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'quiet': True
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([self.url])
            except Exception as primary_error:
                print(f"[WARNING] Primary download failed: {primary_error}")
                # Fallback: try with worst format
                fallback_opts = {
                    'format': 'worst',
                    'outtmpl': os.path.join(self.project_dir, '%(title)s.%(ext)s'),
                    'progress_hooks': [self.progress_hook],
                    'quiet': True
                }
                
                with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                    ydl.download([self.url])

        except Exception as e:
            self.error_signal.emit(str(e))

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            # Try multiple ways to get progress percentage
            percent_val = 0
            
            # Method 1: Try _percent_str
            if '_percent_str' in d:
                percent_str = d['_percent_str'].replace('%', '').strip()
                try:
                    percent_val = int(float(percent_str))
                except:
                    pass
            
            # Method 2: Try calculating from downloaded/total bytes
            if percent_val == 0 and 'downloaded_bytes' in d and 'total_bytes' in d:
                try:
                    downloaded = d['downloaded_bytes']
                    total = d['total_bytes']
                    if total > 0:
                        percent_val = int((downloaded / total) * 100)
                except:
                    pass
            
            # Method 3: Try calculating from downloaded/total bytes_estimate
            if percent_val == 0 and 'downloaded_bytes' in d and 'total_bytes_estimate' in d:
                try:
                    downloaded = d['downloaded_bytes']
                    total = d['total_bytes_estimate']
                    if total > 0:
                        percent_val = int((downloaded / total) * 100)
                except:
                    pass
            
            # Method 4: Handle separate video/audio downloads
            if percent_val == 0 and 'downloaded_bytes' in d and 'total_bytes_estimate' in d:
                try:
                    downloaded = d['downloaded_bytes']
                    total = d['total_bytes_estimate']
                    if total > 0:
                        percent_val = int((downloaded / total) * 100)
                except:
                    pass
            
            # Ensure percentage is within valid range
            percent_val = max(0, min(100, percent_val))
            
            self.progress_signal.emit(percent_val)
            
        elif d['status'] == 'finished':
            if not self._finished:  # Prevent multiple finish signals
                self._finished = True
                self.finished_signal.emit(d['filename'])
class MainWindow(QMainWindow):
    process_result_ready = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("FFMigo Video Editor")
        self.resize(1100, 700)
        
        # Set application icon (only if not already set by main.py)
        if not self.windowIcon():
            app_icon = load_app_icon()
            if app_icon and not app_icon.isNull():
                self.setWindowIcon(app_icon)
        
        # Do not set a window-local stylesheet; rely on application-level stylesheet
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
        
        # Create stacked widget for switching between views
        self.stacked_widget = QStackedWidget()
        self.vbox.addWidget(self.stacked_widget)
        
        # Create containers for each stack
        self.project_stack = QWidget()
        self.content_stack = QWidget()
        
        # Add stacks to stacked widget
        self.stacked_widget.addWidget(self.project_stack)
        self.stacked_widget.addWidget(self.content_stack)
        
        # Create layouts for each stack
        self.project_stack_layout = QVBoxLayout(self.project_stack)
        self.project_stack_layout.setContentsMargins(0, 0, 0, 0)
        self.content_stack_layout = QVBoxLayout(self.content_stack)
        self.content_stack_layout.setContentsMargins(0, 0, 0, 0)
        # Project header with edit and delete options
        self.project_header = QWidget()
        self.project_header_layout = QHBoxLayout(self.project_header)
        self.project_header_layout.setContentsMargins(0, 0, 0, 0)
        self.project_header_layout.setSpacing(12)
        #self.project_header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)  # Center vertically
        

        
        # Project name (left-aligned)
        self.project_name_label = QLabel("FFMigo Video Editor")
        self.project_name_label.setObjectName("ProjectNameLabel")
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
        
        # Icon will be set by _update_all_button_icons()
        
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
        
        # Icon will be set by _update_all_button_icons()
        
        self.project_header_layout.addWidget(self.delete_project_btn)
        
        # Initially hide edit and delete buttons
        self.edit_project_btn.hide()
        self.delete_project_btn.hide()
        
        self.content_stack_layout.addWidget(self.project_header)
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
        # Icon will be set by _update_all_button_icons()
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
        # Icon will be set by _update_all_button_icons()
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
        self.content_stack_layout.addWidget(self.main_content_splitter, stretch=1)
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
        youtube_layout.setSpacing(12)  # Increased spacing between elements
        self.youtube_input = QLineEdit()
        self.youtube_input.setPlaceholderText("Paste YouTube link here...")
        youtube_layout.addWidget(self.youtube_input, stretch=1)  # Give input field more space
        self.youtube_progress = QProgressBar()
        self.youtube_progress.setValue(0)
        self.youtube_progress.setFormat("")  # No text to avoid overlap
        self.youtube_progress.setMinimumWidth(300)  # Much larger minimum width
        self.youtube_progress.setMaximumWidth(400)  # Larger maximum width
        self.youtube_progress.setMinimumHeight(25)  # Make it taller for better visibility
        self.youtube_progress.hide()
        youtube_layout.addWidget(self.youtube_progress)
        self.youtube_widget = QWidget()
        self.youtube_widget.setLayout(youtube_layout)
        self.content_stack_layout.addWidget(self.youtube_widget)
        
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
        # Icon will be set by _update_all_button_icons()
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
        # Icon will be set by _update_all_button_icons()
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
        # Icon will be set by _update_all_button_icons()
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
        self.content_stack_layout.addWidget(self.chat_area, stretch=0)
        
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
        
        # Initialize new project widget
        if not hasattr(self, 'new_project_widget'):
            self._create_new_project_layout()
            self.new_project_widget.show()
        
        self.showMaximized()  # Start maximized, preferred for desktop apps

    def _update_all_button_icons(self):
        """Update all button icons to match current theme"""
        from backend.icon_loader import get_icon
        
        # Play/Pause button
        if hasattr(self, 'play_pause_btn'):
            # Check if media_player exists and is playing
            is_playing = False
            if hasattr(self, 'media_player') and self.media_player:
                is_playing = self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
            
            icon_name = "pause" if is_playing else "play"
            self.play_pause_btn.setIcon(get_icon(icon_name))
        
        # Fullscreen button
        if hasattr(self, 'fullscreen_btn'):
            self.fullscreen_btn.setIcon(get_icon("fullscreen"))
        
        # Action buttons (checkpoint, undo, export, folder)
        if hasattr(self, 'checkpoint_btn'):
            self.checkpoint_btn.setIcon(get_icon("checkpoint"))
        
        if hasattr(self, 'undo_btn'):
            self.undo_btn.setIcon(get_icon("undo"))
        
        if hasattr(self, 'export_btn'):
            self.export_btn.setIcon(get_icon("export"))
        
        if hasattr(self, 'open_dir_btn'):
            self.open_dir_btn.setIcon(get_icon("folder"))
        
        # Project header buttons (edit, delete)
        if hasattr(self, 'edit_project_btn'):
            self.edit_project_btn.setIcon(get_icon("edit"))
        
        if hasattr(self, 'delete_project_btn'):
            self.delete_project_btn.setIcon(get_icon("delete"))
        
        # Sidebar buttons (new project, settings, help)
        if hasattr(self, 'sidebar'):
            if hasattr(self.sidebar, 'new_btn'):
                self.sidebar.new_btn.setIcon(get_icon("new_project", 26))
            if hasattr(self.sidebar, 'settings_btn'):
                self.sidebar.settings_btn.setIcon(get_icon("settings", 26))
            if hasattr(self.sidebar, 'help_btn'):
                self.sidebar.help_btn.setIcon(get_icon("help", 26))
            if hasattr(self.sidebar, 'theme_btn'):
                self.sidebar._update_theme_button_icon()

    def _current_theme(self):
        """Get current theme from config"""
        try:
            cfg = config.get_config()
            return cfg.get('theme', 'dark')
        except Exception:
            return 'dark'

    def update_window_title(self):
        """Update the window title and heading based on current project"""
        if self.project_dir:
            project_name = project_manager.get_project_name(self.project_dir)
            self.setWindowTitle(f"FFMigo Video Editor - {project_name}")
            self.project_name_label.setText(f"{project_name}")
            # Show edit and delete buttons when project is loaded
            self.edit_project_btn.show()
            self.delete_project_btn.show()
            # Update button icons to match theme
            self._update_all_button_icons()
        else:
            self.setWindowTitle("FFMigo Video Editor")
            self.project_name_label.setText("FFMigo Video Editor")
            # Hide edit and delete buttons when no project is loaded
            self.edit_project_btn.hide()
            self.delete_project_btn.hide()
        

    def on_files_dropped(self, file_paths):
        """Handle multiple video files being dropped or selected"""
        if not file_paths:
            return
        
        if len(file_paths) == 1:
            # Single file - use the old behavior
            self._handle_single_video(file_paths[0])
        else:
            # Multiple files - merge them
            self._handle_multiple_videos(file_paths)
    
    def _handle_single_video(self, file_path):
        """Handle a single video file (original behavior)"""
        # Create project dir and copy video
        self.project_dir = project_manager.create_project_dir()
        self.input_path = project_manager.copy_video_to_project(file_path, self.project_dir)
        self.input_ext = os.path.splitext(self.input_path)[1][1:]  # e.g. 'mp4'
        self.processed_path_file = self.input_path  # Set for export functionality
        
        # Initialize video analysis cache
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
    
    def _handle_multiple_videos(self, file_paths):
        """Handle multiple video files by merging them"""
        # Create project directory
        self.project_dir = project_manager.create_project_dir()
        
        # Initialize video analysis cache
        video_analyzer.init_cache(self.project_dir)
        
        # Create output path for merged video
        output_path = os.path.join(self.project_dir, "input.mp4")
        
        # Show merge progress dialog
        from ui.merge_progress_dialog import MergeProgressDialog
        merge_dialog = MergeProgressDialog(file_paths, output_path, self)
        merge_dialog.merge_completed.connect(self._on_merge_completed)
        merge_dialog.merge_failed.connect(self._on_merge_failed)
        merge_dialog.exec()
    
    def _on_merge_completed(self, output_path):
        """Handle successful video merge"""
        self.input_path = output_path
        self.input_ext = os.path.splitext(self.input_path)[1][1:]  # e.g. 'mp4'
        self.processed_path_file = self.input_path  # Set for export functionality
        
        # Analyze the merged video
        self.input_video_analysis = video_analyzer.analyze_video(self.input_path)
        if self.input_video_analysis:
            summary = video_analyzer.get_video_summary(self.input_video_analysis)
            print(f"[INFO] Merged video analysis: {summary}")
        
        # Set UI state for project loaded
        self.set_ui_state_for_project_loaded()
        
        # Load video and update UI
        self.load_video(self.input_path)
        self.chat_log.clear()
        self.append_chat_log("System", "Videos merged successfully. Ready for commands.")
        self.refresh_project_list(select=self.project_dir)
        self.update_window_title()
    
    def _on_merge_failed(self, error_message):
        """Handle failed video merge"""
        QMessageBox.critical(self, "Merge Failed", f"Failed to merge videos:\n{error_message}")
        # Reset to no project state
        self.project_dir = None
        self.input_path = None
        self.input_ext = None
        self.processed_path_file = None
        self.input_video_analysis = None

    def download_youtube_video(self):
        url = self.youtube_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a YouTube link.")
            return
        
        # Prevent multiple downloads
        if hasattr(self, 'youtube_thread') and self.youtube_thread.isRunning():
            print("[WARNING] Download already in progress")
            return
        
        # Reset progress bar
        self.youtube_progress.setValue(0)
        self.youtube_progress.show()
        
        # Disable download button during download
        #self.youtube_download_btn.setEnabled(False)
        self.youtube_input.setEnabled(False)

        # Use the proper project manager to create project directory
        self.project_dir = project_manager.create_project_dir()
        print(f"[INFO] Created project directory for YouTube download: {self.project_dir}")

        self.youtube_thread = YouTubeDownloader(url, self.project_dir)
        self.youtube_thread.progress_signal.connect(self.youtube_progress.setValue)
        self.youtube_thread.finished_signal.connect(self.youtube_download_finished)
        self.youtube_thread.error_signal.connect(self.youtube_download_error)
        self.youtube_thread.start()
    def youtube_download_finished(self, file_path):
        self.youtube_progress.hide()
        
        # Re-enable controls
        #self.youtube_download_btn.setEnabled(True)
        self.youtube_input.setEnabled(True)
        
        # Check if file actually exists
        if not os.path.exists(file_path):
            print(f"[ERROR] Downloaded file does not exist: {file_path}")
            QMessageBox.critical(self, "Download Error", f"Downloaded file not found: {file_path}")
            return
        
        # Validate the downloaded video has both video and audio streams
        if not self._validate_video_streams(file_path):
            QMessageBox.warning(self, "Download Warning", 
                              "Video downloaded but may not have audio. This could be due to:\n"
                              "1. The original video has no audio\n"
                              "2. Audio stream extraction failed\n"
                              "You can still edit the video, but it will be silent.")
        
        # Get the actual file extension from the downloaded file
        actual_ext = os.path.splitext(file_path)[1]
        
        # Keep the original extension to preserve video+audio
        # Don't force rename to .mp4 if it's actually a .webm file
        new_file_path = os.path.join(self.project_dir, f"input{actual_ext}")
        
        try:
            import shutil
            shutil.move(file_path, new_file_path)
            print(f"[INFO] Renamed downloaded file from {file_path} to {new_file_path}")
        except Exception as e:
            print(f"[ERROR] Failed to rename downloaded file: {e}")
            QMessageBox.warning(self, "Warning", f"Download completed but failed to rename file: {e}")
            # Still try to load the project with the original filename
            new_file_path = file_path
        
        # Set up the project state like normal video handling
        self.input_path = new_file_path
        self.input_ext = os.path.splitext(self.input_path)[1][1:]  # e.g. 'mp4'
        self.processed_path_file = self.input_path  # Set for export functionality
        
        # Initialize video analysis cache
        video_analyzer.init_cache(self.project_dir)
        
        # Analyze the input video on first load
        self.input_video_analysis = video_analyzer.analyze_video(self.input_path)
        if self.input_video_analysis:
            summary = video_analyzer.get_video_summary(self.input_video_analysis)
            print(f"[INFO] YouTube video analysis: {summary}")
        
        # Set UI state for project loaded
        self.set_ui_state_for_project_loaded()
        
        # Load video and update UI
        self.load_video(self.input_path)
        self.chat_log.clear()
        self.append_chat_log("System", "YouTube video downloaded and loaded. Ready for commands.")
        self.refresh_project_list(select=self.project_dir)
        self.update_window_title()
        
        QMessageBox.information(self, "Download Complete", f"YouTube video downloaded successfully!")

    def _validate_video_streams(self, file_path):
        """Check if the video file has both video and audio streams"""
        try:
            import subprocess
            import json
            
            # Use ffprobe to check streams
            cmd = [
                'ffprobe', 
                '-v', 'quiet', 
                '-print_format', 'json', 
                '-show_streams', 
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            streams_info = json.loads(result.stdout)
            
            video_streams = [s for s in streams_info.get('streams', []) if s['codec_type'] == 'video']
            audio_streams = [s for s in streams_info.get('streams', []) if s['codec_type'] == 'audio']
            
            has_video = len(video_streams) > 0
            has_audio = len(audio_streams) > 0
            
            
            if has_video and not has_audio:
                print("[WARNING] Video has no audio stream")
            elif not has_video and has_audio:
                print("[WARNING] File has only audio, no video")
            elif not has_video and not has_audio:
                print("[WARNING] File has neither video nor audio")
            
            return has_video and has_audio
            
        except Exception as e:
            print(f"[WARNING] Could not validate video streams: {e}")
            return True  # Assume it's valid if we can't check
    def youtube_download_error(self, error_msg):
        self.youtube_progress.hide()
        
        # Re-enable controls
        #self.youtube_download_btn.setEnabled(True)
        self.youtube_input.setEnabled(True)
        
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
        from ui.about_dialog import AboutDialog
        dlg = AboutDialog(self.app_config, self)
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
        
        # Use the restored file path directly
        self.input_path = restored_file_path
        self.input_ext = os.path.splitext(restored_file_path)[1][1:]
        
        # Force stop the current video player before loading the new one
        try:
            self.media_player.stop()
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

    def save_settings(self, settings):
        self.app_config = settings
        config.save_config(settings)
        self.append_chat_log("System", "Settings updated.")

    def update_processed_video(self, video_path):
        try:
            # Update the video player with the new processed video
            self.load_video(video_path)
            self.media_controls.show()
            self.export_btn.setEnabled(True)
            self.open_dir_btn.setEnabled(True)  # Keep open directory enabled after processing
            self.checkpoint_btn.setEnabled(True)  # Enable checkpoints after processing
            self.processed_path_file = video_path  # Update for export functionality
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
        # Update the play/pause icon using the theming system
        self._update_all_button_icons()

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
        if not self.input_path or not os.path.exists(self.input_path):
            QMessageBox.warning(self, "Export Failed", "No video to export.")
            return
        
        # Force enable the button just in case
        self.export_btn.setEnabled(True)
        
        default_dir = self.app_config.get('export_dir', os.path.expanduser('~'))
        suggested_name = os.path.basename(self.input_path)
        
        fname, _ = QFileDialog.getSaveFileName(self, "Export Video", os.path.join(default_dir, suggested_name))
        
        if fname:
            try:
                import shutil
                shutil.copy2(self.input_path, fname)
                QMessageBox.information(self, "Export", f"Exported to {fname}")
            except Exception as e:
                QMessageBox.warning(self, "Export Failed", str(e))

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
            input_video_info = video_analyzer.get_video_summary(self.input_video_analysis)
        
        # Get FFmpeg command from LLM
        try:
            import os
            input_filename = os.path.basename(self.input_path)
            
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
                return
            if ffmpeg_result and ffmpeg_result.get('success'):
                if new_input_file and new_input_ext:
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
        projects = project_manager.list_projects()
        self.sidebar.set_projects(projects, selected=select or self.project_dir)

    def set_ui_state_for_no_project(self):
        """Set UI state when no project is loaded (app startup or new project)"""
        # Switch to new project view
        self.stacked_widget.setCurrentWidget(self.project_stack)
        
        # Disable action buttons
        self.export_btn.setEnabled(False)
        self.open_dir_btn.setEnabled(False)
        self.checkpoint_btn.setEnabled(False)
        self.undo_btn.setEnabled(False)
        
        # Update window title
        self.project_name_label.hide()
        
        # Create professional new project layout
        #self._create_new_project_layout()
        
        # Show the new project layout
        #self.new_project_widget.show()

    def _create_new_project_layout(self):
        """Create a professional new project layout with two main options"""
        # Remove existing new project widget if it exists
        if hasattr(self, 'new_project_widget'):
            self.new_project_widget.deleteLater()
        
        # Create main container
        self.new_project_widget = QWidget()
        self.new_project_widget.setObjectName("NewProjectContainer")
        
        # Main layout
        main_layout = QVBoxLayout(self.new_project_widget)
        main_layout.setContentsMargins(60, 40, 60, 40)
        main_layout.setSpacing(24)  # Reduced spacing between elements
        # Welcome header
        welcome_header = QWidget()
        welcome_layout = QVBoxLayout(welcome_header)
        welcome_layout.setContentsMargins(0, 0, 0, 0)
        welcome_layout.setSpacing(12)
        
        title = QLabel("Create New Project")
        title.setObjectName("NewProjectTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        
        subtitle = QLabel("Choose how you'd like to add your video content")
        subtitle.setObjectName("NewProjectSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        
        welcome_layout.addWidget(title)
        welcome_layout.addWidget(subtitle)
        main_layout.addWidget(welcome_header)
        
        # Two-column layout for options
        options_container = QWidget()
        options_container.setContentsMargins(0, 100, 0, 0)  # Add top margin to push options down
        options_layout = QHBoxLayout(options_container)
        options_layout.setContentsMargins(0, 0, 0, 0)
        options_layout.setSpacing(40)
        
        # Left column: Drag & Drop
        drag_drop_column = QWidget()
        drag_drop_column.setObjectName("DragDropColumn")
        drag_drop_column.setFixedWidth(400)
        drag_drop_layout = QVBoxLayout(drag_drop_column)
        drag_drop_layout.setContentsMargins(0, 0, 0, 0)
        drag_drop_layout.setSpacing(20)
        
        # Drag & Drop header
        drag_header = QLabel("Upload Local Video")
        drag_header.setObjectName("OptionHeader")
        drag_header.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        drag_drop_layout.addWidget(drag_header)
        
        # Drag & Drop description
        drag_desc = QLabel("Drag and drop video files here or click to browse")
        drag_desc.setObjectName("OptionDescription")
        drag_desc.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        drag_desc.setWordWrap(True)
        drag_drop_layout.addWidget(drag_desc)
        
        # Enhanced drag & drop area
        enhanced_dragdrop = self._create_enhanced_dragdrop()
        drag_drop_layout.addWidget(enhanced_dragdrop)
        
        # Supported formats
        formats_label = QLabel("Supported: MP4, MOV, AVI, MKV, WebM, FLV, WMV")
        formats_label.setObjectName("FormatsLabel")
        formats_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        drag_drop_layout.addWidget(formats_label)
        
        # Right column: YouTube Download
        youtube_column = QWidget()
        youtube_column.setObjectName("YouTubeColumn")
        youtube_column.setFixedWidth(400)
        youtube_layout = QVBoxLayout(youtube_column)
        youtube_layout.setContentsMargins(0, 0, 0, 0)
        youtube_layout.setSpacing(20)
        
        # YouTube header
        youtube_header = QLabel("Download from YouTube")
        youtube_header.setObjectName("OptionHeader")
        youtube_header.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        youtube_layout.addWidget(youtube_header)
        
        # YouTube description
        youtube_desc = QLabel("Paste a YouTube link to download and edit the video")
        youtube_desc.setObjectName("OptionDescription")
        youtube_desc.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        youtube_desc.setWordWrap(True)
        youtube_layout.addWidget(youtube_desc)
        
        # Enhanced YouTube download area
        enhanced_youtube = self._create_enhanced_youtube_download()
        youtube_layout.addWidget(enhanced_youtube)
        
        # YouTube info
        youtube_info = QLabel("Downloads best quality available")
        youtube_info.setObjectName("YouTubeInfo")
        youtube_info.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        youtube_layout.addWidget(youtube_info)
        
        # Add columns to options container
        options_layout.addStretch(1)
        options_layout.addWidget(drag_drop_column)
        options_layout.addWidget(youtube_column)
        options_layout.addStretch(1)
        
        main_layout.addWidget(options_container)
        
        # Add to main layout with stretch after to push content to top
        self.project_stack_layout.addWidget(self.new_project_widget)
        self.project_stack_layout.addStretch(1)  # Add stretch only after content to push it up

    def _create_enhanced_dragdrop(self):
        """Create an enhanced drag and drop widget"""
        container = QWidget()
        container.setObjectName("EnhancedDragDropContainer")
        container.setMinimumHeight(280)
        container.setMaximumHeight(320)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Icon
        icon_label = QLabel()
        icon_label.setObjectName("DragDropIcon")
        icon_label.setFixedSize(55, 55)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_label.setText("📁")
                   
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Text
        text_label = QLabel("Drag & Drop Video Files Here")
        text_label.setObjectName("DragDropText")
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(text_label)
        
        # Subtext
        subtext_label = QLabel("or click to browse files")
        subtext_label.setObjectName("DragDropSubtext")
        subtext_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtext_label)
        
        # Create a drag drop widget for handling drops and clicks
        drag_drop_handler = DragDropWidget()
        drag_drop_handler.files_dropped.connect(self.on_files_dropped)
        
        # Make the container accept drops and handle clicks
        container.setAcceptDrops(True)
        container.dragEnterEvent = lambda event: drag_drop_handler.dragEnterEvent(event)
        container.dropEvent = lambda event: drag_drop_handler.dropEvent(event)
        container.mousePressEvent = lambda event: drag_drop_handler.mousePressEvent(event)
        
        return container

    def _create_enhanced_youtube_download(self):
        """Create an enhanced YouTube download widget"""
        container = QWidget()
        container.setObjectName("EnhancedYouTubeContainer")
        container.setMinimumHeight(280)
        container.setMaximumHeight(320)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Icon
        icon_label = QLabel()
        icon_label.setObjectName("YouTubeIcon")
        icon_label.setFixedSize(50, 50)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setText("▶")
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Input field
        input_container = QWidget()
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(12)
        input_container.setObjectName("YouTubeInputContainer")
            
        # URL input
        self.youtube_input.setPlaceholderText("Paste YouTube URL and press Enter to download...")
        self.youtube_input.setObjectName("YouTubeUrlInput")
        # Connect Enter key press to download function
        self.youtube_input.returnPressed.connect(self.download_youtube_video)
        input_layout.addWidget(self.youtube_input)
        
        # Progress bar
        self.youtube_progress.setObjectName("YouTubeProgressBar")
        input_layout.addWidget(self.youtube_progress)
        
        layout.addWidget(input_container)
        
        return container

    def set_ui_state_for_project_loaded(self):
        """Set UI state when a project is loaded with video"""
        # Show video and terminal widgets first
        self.video_player_widget.show()
        self.terminal_widget.show()
        self.media_controls.show()
        
        # Switch to content view
        self.stacked_widget.setCurrentWidget(self.content_stack)
        
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
        # Reset state and show new project layout
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
        self.append_chat_log("System", "Create a new project by uploading a video or downloading from YouTube.")
        self.update_window_title()

    def rename_project(self, proj_dir):
        from PyQt6.QtWidgets import QInputDialog
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
        self.export_btn.setEnabled(True)  # Always enable export button
        
        # Enable undo button if there are checkpoints available
        checkpoints = project_manager.list_checkpoints(self.project_dir)
        self.undo_btn.setEnabled(len(checkpoints) > 0)
        
        # Clear chat and show message
        self.chat_log.clear()
        self.append_chat_log("System", "Project loaded. Ready for commands.")
        self.update_window_title()

    def load_video(self, video_path):
        try:
            url = QUrl.fromLocalFile(video_path)
            # Stop and delete the media player and audio output
            try:
                self.media_player.stop()
                self.media_player.setSource(QUrl())
                del self.media_player
                del self.audio_output
            except Exception as e:
                pass
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._create_and_load_player(video_path))
        except Exception as e:
            print(f'[ERROR] Exception in load_video: {e}')
            import traceback; traceback.print_exc()
            self.append_chat_log("Error", f"Exception loading video: {e}")
            return

    def _create_and_load_player(self, video_path):
        try:
            from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
            url = QUrl.fromLocalFile(video_path)
            self.media_player = QMediaPlayer()
            self.audio_output = QAudioOutput()
            self.media_player.setVideoOutput(self.video_widget)
            self.media_player.setAudioOutput(self.audio_output)
            self.media_player.playbackStateChanged.connect(self.update_play_pause_icon)
            self.media_player.positionChanged.connect(self.update_position)
            self.media_player.durationChanged.connect(self.update_duration)
            self.media_player.errorOccurred.connect(self.handle_media_error)
            self.media_player.setSource(url)
            self.media_player.pause()
            self.processed_path_file = video_path
            self.seek_slider.setValue(0)
            self.seek_slider.setRange(0, 0)
            self.time_label.setText("00:00 / 00:00")
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
