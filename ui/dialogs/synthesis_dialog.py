from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QComboBox, QPushButton, QMessageBox
from PySide6.QtCore import Qt
import pandas as pd
import time

from core import synthesis
from core.worker_thread import WorkerThread
from ui.dialogs.progress_dialog import ProgressDialog

class SynthesisDialog(QDialog):
    """Dialog for configuring data synthesis parameters."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Data Synthesis")
        self.setModal(True)
        self.setGeometry(100, 100, 400, 250)
        self.current_df = None
        self.result_df = None
        self.result_config = None
        self._is_active = True  # Track if dialog is still valid
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Synthesis mode selection
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Synthesis Mode:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Gaussian Copula", "CTGAN", "TVAE"])
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo)
        layout.addLayout(mode_layout)
        
        # Rows to generate
        rows_layout = QHBoxLayout()
        rows_label = QLabel("Number of Rows:")
        self.rows_spinbox = QSpinBox()
        self.rows_spinbox.setMinimum(1)
        self.rows_spinbox.setMaximum(100000)
        self.rows_spinbox.setValue(1000)
        rows_layout.addWidget(rows_label)
        rows_layout.addWidget(self.rows_spinbox)
        layout.addLayout(rows_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.synthesize_btn = QPushButton("Synthesize")
        self.cancel_btn = QPushButton("Cancel")
        self.synthesize_btn.clicked.connect(self._on_synthesize)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.synthesize_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)

    def set_dataframe(self, df: pd.DataFrame) -> None:
        """Set the dataframe to synthesize."""
        self.current_df = df

    def _on_synthesize(self) -> None:
        """Handle synthesis button click."""
        if self.current_df is None:
            QMessageBox.warning(self, "Error", "No dataframe loaded.")
            return
        
        mode = self.mode_combo.currentText()
        num_rows = self.rows_spinbox.value()
        
        # Map UI text to model type
        model_map = {
            "Gaussian Copula": "gaussian_copula",
            "CTGAN": "ctgan",
            "TVAE": "tvae"
        }
        model_type = model_map[mode]
        
        # Create worker thread
        self.worker = WorkerThread(
            func=synthesis.synthesize,
            kwargs={
                "df": self.current_df,
                "num_rows": num_rows,
                "model_type": model_type,
                "evaluate": True
            }
        )
        
        # Create progress dialog
        self.progress_dialog = ProgressDialog(f"Synthesizing data with {mode}...", self, allow_cancel=True)
        
        # Connect worker signals
        self.worker.progress.connect(self.progress_dialog.set_progress)
        self.worker.status.connect(self.progress_dialog.set_status)
        self.worker.completed.connect(self._on_synthesis_complete)
        self.worker.error.connect(self._on_synthesis_error)
        self.worker.cancelled.connect(self._on_synthesis_cancelled)
        
        # Set cancel callback
        self.progress_dialog.set_cancel_callback(self.worker.request_cancel)
        
        # Disable synthesis button
        self.synthesize_btn.setEnabled(False)
        
        # Start worker
        self.worker.start()
        
        # Show progress dialog (blocks user interaction but not the event loop)
        self.progress_dialog.exec()
    
    def _on_synthesis_complete(self, result):
        """Handle synthesis completion."""
        if not self._is_active:
            return
        
        self.result_df, self.result_config = result
        self.synthesize_btn.setEnabled(True)
        self.progress_dialog.accept()
        
        # Clean up worker - non-blocking
        self._cleanup_worker(timeout_ms=1000)
        
        self.accept()
    
    def _on_synthesis_cancelled(self):
        """Handle synthesis cancellation."""
        if not self._is_active:
            return
        
        self.synthesize_btn.setEnabled(True)
        
        # Close progress dialog if still open
        if self.progress_dialog and self.progress_dialog.isVisible():
            self.progress_dialog.mark_cancelled()
            self.progress_dialog.accept()
        
        # Clean up worker - non-blocking
        self._cleanup_worker(request_cancel=True, timeout_ms=1000)
        
        # Show cancellation message
        QMessageBox.information(self, "Cancelled", "Synthesis operation was cancelled.")
        self.reject()
    
    def _on_synthesis_error(self, error_msg: str):
        """Handle synthesis error."""
        if not self._is_active:
            return
        
        self.synthesize_btn.setEnabled(True)
        self.progress_dialog.accept()
        
        # Clean up worker - non-blocking
        self._cleanup_worker(timeout_ms=1000)
        
        QMessageBox.critical(
            self,
            "Synthesis Error",
            f"Failed to synthesize data:\n\n{error_msg}"
        )

    def closeEvent(self, event):
        """Handle dialog close event."""
        self._is_active = False
        
        # Clean up worker if still running - non-blocking
        self._cleanup_worker(request_cancel=True, timeout_ms=500)
        
        super().closeEvent(event)

    def _cleanup_worker(self, request_cancel=False, timeout_ms=1000):
        """
        Clean up worker thread safely without blocking UI.
        
        Args:
            request_cancel: If True, request cancellation before quitting
            timeout_ms: Timeout in milliseconds for the thread to finish
        """
        if not hasattr(self, 'worker') or not self.worker:
            return
        
        try:
            if request_cancel and self.worker.isRunning():
                self.worker.request_cancel()
            
            # Request the thread to quit
            self.worker.quit()
            
            # Don't wait indefinitely - use a reasonable wait time
            # PySide6's wait() doesn't support timeout, so we check repeatedly
            start_time = time.time()
            timeout_s = timeout_ms / 1000.0
            
            while self.worker.isRunning() and time.time() - start_time < timeout_s:
                time.sleep(0.01)
            
            # If the thread is still running, force clean up
            if self.worker.isRunning():
                print("Warning: Worker thread did not finish, forcing cleanup")
                # Try to force the process to stop
                if hasattr(self.worker, '_process') and self.worker._process:
                    if self.worker._process.is_alive():
                        self.worker._process.terminate()
                        self.worker._process.join(timeout=1)
                        if self.worker._process.is_alive():
                            self.worker._process.kill()
                            self.worker._process.join(timeout=1)
        except Exception as e:
            print(f"Error cleaning up worker: {e}")

    def get_results(self) -> tuple:
        """Return synthesized dataframe and config."""
        return self.result_df, self.result_config

    def get_parameters(self):
        """Return selected parameters."""
        return {
            "mode": self.mode_combo.currentText(),
            "rows": self.rows_spinbox.value()
        }