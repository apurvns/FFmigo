from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QTextEdit, QFrame
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
import threading
import time

class MergeProgressDialog(QDialog):
    merge_completed = pyqtSignal(str)  # Emits the output path when merge is complete
    merge_failed = pyqtSignal(str)     # Emits error message when merge fails
    progress_updated = pyqtSignal(int, str)  # Emits progress updates (percent, message)
    
    def __init__(self, video_paths, output_path, parent=None):
        super().__init__(parent)
        self.video_paths = video_paths
        self.output_path = output_path
        self.merger = None
        self.merge_thread = None
        self.merge_completed.connect(self.accept)  # Auto-close on completion
        self.merge_failed.connect(self.reject)     # Auto-close on failure
        
        self.setWindowTitle("Merging Videos")
        self.setFixedSize(500, 400)
        self.setModal(True)
        
        # Prevent closing during merge
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        
        self.setup_ui()
        self.start_merge()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Merging Videos")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)
        
        # Video count and order
        count_label = QLabel(f"Merging {len(self.video_paths)} videos in the following order:")
        count_label.setFont(QFont("Arial", 10))
        layout.addWidget(count_label)
        
        # Video list
        self.video_list = QTextEdit()
        self.video_list.setMaximumHeight(120)
        self.video_list.setReadOnly(True)
        # Use theme colors instead of custom styling
        self.video_list.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                font-family: monospace;
                font-size: 11px;
            }
        """)
        
        # Show video list
        video_text = ""
        for i, path in enumerate(self.video_paths, 1):
            filename = path.split('/')[-1] if '/' in path else path.split('\\')[-1]
            video_text += f"{i:2d}. {filename}\n"
        self.video_list.setPlainText(video_text)
        layout.addWidget(self.video_list)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Progress section
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(8)
        
        # Status label
        self.status_label = QLabel("Analyzing videos...")
        self.status_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        progress_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ddd;
                border-radius: 6px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #a259ff;
                border-radius: 4px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        
        # Details label
        self.details_label = QLabel("")
        self.details_label.setWordWrap(True)
        self.details_label.setStyleSheet("color: #666; font-size: 11px;")
        progress_layout.addWidget(self.details_label)
        
        layout.addLayout(progress_layout)
        
        # Cancel button (initially enabled)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(True)  # Enable cancel button
        self.cancel_btn.clicked.connect(self.cancel_merge)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)
        
        # Connect signals
        self.progress_updated.connect(self._update_progress)
    
    def start_merge(self):
        """Start the merge process in a background thread"""
        from backend.video_merger import VideoMerger
        
        self.merger = VideoMerger()
        self.merge_thread = threading.Thread(target=self._run_merge, daemon=True)
        self.merge_thread.start()
    
    def _run_merge(self):
        """Run the merge process in background thread"""
        try:
            # Update progress callback to emit signals to main thread
            def progress_callback(percent, message):
                # Emit signal to main thread
                self.progress_updated.emit(percent, message)
            
            # Run the merge
            result = self.merger.merge_videos(
                self.video_paths, 
                self.output_path, 
                progress_callback
            )
            
            # Emit result
            if result.get('success'):
                self.merge_completed.emit(self.output_path)
            else:
                error_msg = result.get('error', 'Unknown error occurred')
                if not error_msg and result.get('stderr'):
                    error_msg = result.get('stderr')
                self.merge_failed.emit(error_msg)
                
        except Exception as e:
            self.merge_failed.emit(str(e))
    
    def _update_progress(self, percent, message):
        """Update progress bar and status (called from main thread via signal)"""
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)
        
        # Update details based on progress
        if percent == 0:
            self.details_label.setText("Checking video compatibility...")
        elif percent < 50:
            self.details_label.setText("Processing videos...")
        elif percent < 100:
            self.details_label.setText("Finalizing merge...")
        else:
            self.details_label.setText("Merge completed successfully!")
    
    def cancel_merge(self):
        """Cancel the merge process"""
        # Close the dialog immediately
        self.reject()
    
    def closeEvent(self, event):
        """Handle close events"""
        if self.merge_thread and self.merge_thread.is_alive():
            # If merge is still running, ask user if they want to cancel
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, 
                "Cancel Merge", 
                "Merge is still in progress. Are you sure you want to cancel?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept() 