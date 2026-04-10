"""
Worker thread utilities for running long-running operations without blocking the UI.
"""

from PySide6.QtCore import QThread, Signal
from typing import Callable, Any, Tuple
import traceback


class WorkerThread(QThread):
    """
    Worker thread for running long-running operations off the main thread.
    
    Emits signals for progress tracking and completion handling.
    Supports graceful cancellation of operations.
    """
    
    # Signal emitted with progress (0-100)
    progress = Signal(int)
    
    # Signal emitted with status message
    status = Signal(str)
    
    # Signal emitted when operation completes successfully with results
    completed = Signal(object)
    
    # Signal emitted when an error occurs during operation
    error = Signal(str)
    
    # Signal emitted when operation is cancelled
    cancelled = Signal()
    
    def __init__(self, func: Callable, args: Tuple = (), kwargs: dict = None):
        """
        Initialize worker thread.
        
        Args:
            func: Callable function to run in the thread
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
        """
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self._result = None
        self._cancel_requested = False
    
    def request_cancel(self):
        """Request cancellation of the operation."""
        self._cancel_requested = True
        self.status.emit("Cancelling operation...")
    
    def cancel_requested(self) -> bool:
        """Check if cancellation has been requested."""
        return self._cancel_requested
    
    def run(self):
        """Execute the worker function in the thread."""
        try:
            self.status.emit("Starting operation...")
            self.progress.emit(0)
            
            # Check for cancellation before starting
            if self._cancel_requested:
                self.cancelled.emit()
                return
            
            # Run the function
            result = self.func(*self.args, **self.kwargs)
            
            # Check for cancellation after completion
            if self._cancel_requested:
                self.cancelled.emit()
                return
            
            self._result = result
            self.progress.emit(100)
            self.status.emit("Operation completed!")
            self.completed.emit(result)
            
        except Exception as e:
            # Don't emit error if operation was cancelled
            if self._cancel_requested:
                self.cancelled.emit()
            else:
                error_msg = f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}"
                self.error.emit(error_msg)
    
    def get_result(self):
        """Get the result from the completed operation."""
        return self._result
