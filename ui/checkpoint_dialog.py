from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, QMessageBox,
                             QFrame, QScrollArea, QWidget, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
import os
from datetime import datetime
from backend import project_manager

class CheckpointItemWidget(QWidget):
    """Custom widget for displaying checkpoint information"""
    restore_requested = pyqtSignal()  # Signal emitted when restore button is clicked
    
    def __init__(self, checkpoint_num, meta, parent=None):
        super().__init__(parent)
        self.checkpoint_num = checkpoint_num
        self.meta = meta
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        
        # Header with checkpoint number and timestamp
        header_layout = QHBoxLayout()
        
        checkpoint_label = QLabel(f"Checkpoint {checkpoint_num}")
        checkpoint_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        checkpoint_label.setObjectName("CheckpointLabel")
        header_layout.addWidget(checkpoint_label)
        
        header_layout.addStretch()
        
        # Format timestamp
        timestamp = meta.get('timestamp', 0)
        if timestamp:
            dt = datetime.fromtimestamp(timestamp)
            time_str = dt.strftime("%H:%M:%S")
            time_label = QLabel(time_str)
            time_label.setObjectName("CheckpointTimeLabel")
            header_layout.addWidget(time_label)
        
        layout.addLayout(header_layout)
        
        # User command
        user_cmd = meta.get('user_command', 'Unknown operation')
        cmd_label = QLabel(f"Command: {user_cmd}")
        cmd_label.setWordWrap(True)
        cmd_label.setObjectName("CheckpointCmdLabel")
        layout.addWidget(cmd_label)
        
        # File info
        file_size = meta.get('file_size', 0)
        if file_size:
            size_mb = file_size / (1024 * 1024)
            file_label = QLabel(f"File: {meta.get('input_file', 'Unknown')} ({size_mb:.1f} MB)")
            file_label.setObjectName("CheckpointFileLabel")
            layout.addWidget(file_label)
        
        # Restore button with icon and proper sizing
        restore_btn = QPushButton()
        restore_btn.setObjectName("RestoreCheckpointButton")
        restore_btn.setFixedHeight(32)
        restore_btn.setFixedWidth(120)  # Fixed width instead of full width
        restore_btn.clicked.connect(self.restore_requested)
        
        # Set icon and text using dynamic icon system
        from backend.icon_loader import get_icon
        restore_btn.setIcon(get_icon("undo", 16))
        restore_btn.setText("Restore")
        
        layout.addWidget(restore_btn, alignment=Qt.AlignmentFlag.AlignRight)
        
        # Add separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setObjectName("CheckpointSeparator")
        layout.addWidget(separator)

class CheckpointDialog(QDialog):
    checkpoint_restored = pyqtSignal(int, str)  # Signal emitted when checkpoint is restored (checkpoint_num, restored_file_path)
    
    def __init__(self, project_dir, parent=None):
        super().__init__(parent)
        self.project_dir = project_dir
        self.setObjectName("CheckpointDialog")
        self.setWindowTitle("Video Checkpoints")
        self.setMinimumWidth(400)
        
        # Set up UI
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header
        header = QLabel("Restore to Previous State")
        header.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header.setObjectName("CheckpointHeaderLabel")
        layout.addWidget(header)
        
        # Description
        desc = QLabel("Select a checkpoint to restore your video to that previous state. All changes after that point will be lost.")
        desc.setWordWrap(True)
        desc.setObjectName("CheckpointDescLabel")
        layout.addWidget(desc)
        
        # Scrollable checkpoint list
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setObjectName("CheckpointScrollArea")
        # Ensure viewport can be targeted by QSS
        self.scroll_area.viewport().setObjectName("CheckpointScrollViewport")
        
        self.checkpoint_widget = QWidget()
        self.checkpoint_layout = QVBoxLayout(self.checkpoint_widget)
        self.checkpoint_layout.setContentsMargins(0, 0, 0, 0)
        self.checkpoint_layout.setSpacing(0)
        
        self.scroll_area.setWidget(self.checkpoint_widget)
        layout.addWidget(self.scroll_area, stretch=1)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.setObjectName("DialogCloseButton")
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
        # Load checkpoints
        self.load_checkpoints()
    
    def load_checkpoints(self):
        """Load and display all available checkpoints"""
        # Clear existing items
        for i in reversed(range(self.checkpoint_layout.count())):
            child = self.checkpoint_layout.itemAt(i).widget()
            if child:
                child.deleteLater()
        
        # Get checkpoints
        checkpoints = project_manager.list_checkpoints(self.project_dir)
        
        if not checkpoints:
            # No checkpoints available
            no_checkpoints = QLabel("No checkpoints available.\nCheckpoints are created automatically before each operation.")
            no_checkpoints.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_checkpoints.setObjectName("NoCheckpointsLabel")
            self.checkpoint_layout.addWidget(no_checkpoints)
            return
        
        # Add checkpoints in reverse order (newest first)
        for checkpoint_num, meta in reversed(checkpoints):
            item_widget = CheckpointItemWidget(checkpoint_num, meta)
            item_widget.restore_requested.connect(lambda num=checkpoint_num: self.restore_checkpoint(num))
            self.checkpoint_layout.addWidget(item_widget)
    
    def restore_checkpoint(self, checkpoint_num):
        """Restore the selected checkpoint"""
        reply = QMessageBox.question(
            self, 
            "Confirm Restore", 
            f"Are you sure you want to restore to Checkpoint {checkpoint_num}?\n\nThis will undo all changes made after this point.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success, result = project_manager.restore_checkpoint(self.project_dir, checkpoint_num)
            
            if success:
                self.checkpoint_restored.emit(checkpoint_num, result) # Pass the restored file path
                self.close()
            else:
                QMessageBox.warning(self, "Restore Failed", f"Failed to restore checkpoint: {result}")
    
    def showEvent(self, event):
        """Update button icons when dialog is shown"""
        super().showEvent(event)
        # Update all restore button icons to match current theme
        self._update_button_icons()
    
    def _update_button_icons(self):
        """Update all button icons in the dialog"""
        from backend.icon_loader import get_icon
        
        # Find all restore buttons and update their icons
        for i in range(self.checkpoint_layout.count()):
            item = self.checkpoint_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'findChildren'):
                    # Find restore buttons in the widget
                    restore_buttons = widget.findChildren(QPushButton, "RestoreCheckpointButton")
                    for btn in restore_buttons:
                        btn.setIcon(get_icon("undo", 16)) 