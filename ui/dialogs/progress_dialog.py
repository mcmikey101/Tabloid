"""
Progress dialog for displaying long-running operation status.
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton
from PySide6.QtCore import Qt, QTimer
from typing import Optional, Callable


class ProgressDialog(QDialog):
    """
    Modal dialog showing progress of a long-running operation.
    """
    
    def __init__(self, title: str = "Processing", parent=None, allow_cancel: bool = True):
        """
        Initialize progress dialog.
        
        Args:
            title: Window title and main label text
            parent: Parent widget
            allow_cancel: Whether to show a cancel button (default: True)
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)  # Hide X button
        self.resize(400, 150)
        
        self.allow_cancel = allow_cancel
        self._cancel_callback: Optional[Callable] = None
        
        self._init_ui(title)
    
    def _init_ui(self, title: str):
        """Initialize UI elements."""
        layout = QVBoxLayout(self)
        
        # Title label
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.title_label)
        
        # Status label
        self.status_label = QLabel("Starting...")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Cancel button (enabled by default)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        layout.addWidget(self.cancel_btn)
    
    def set_progress(self, value: int):
        """
        Update progress bar value.
        
        Args:
            value: Progress value (0-100)
        """
        self.progress_bar.setValue(max(0, min(100, value)))
    
    def set_status(self, message: str):
        """
        Update status message.
        
        Args:
            message: Status message to display
        """
        self.status_label.setText(message)
    
    def set_cancel_callback(self, callback: Callable):
        """
        Set callback function to run when cancel is clicked.
        
        Args:
            callback: Function to call on cancel
        """
        self._cancel_callback = callback
    
    def _on_cancel_clicked(self):
        """Handle cancel button click."""
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("Cancelling...")
        self.status_label.setText("Waiting for operation to stop...")
        if self._cancel_callback:
            self._cancel_callback()
        # Close the dialog after requesting cancellation
        # This prevents the UI from appearing frozen
        QTimer.singleShot(100, self.accept)
    
    def mark_cancelled(self):
        """Mark the dialog as cancelled and update UI."""
        self.status_label.setText("Cancellation requested")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("Cancelled")

