"""
Worker thread utilities for running long-running operations without blocking the UI.
Implements true cancellation using multiprocessing.
"""

from PySide6.QtCore import QThread, Signal, QTimer
from typing import Callable, Any, Tuple, Optional
import multiprocessing as mp
import queue
import traceback
import time
import atexit
import gc


class WorkerProcessException(Exception):
    """Exception raised when a worker process fails."""
    pass


# Global for inter-process communication
_cancel_event: Optional[mp.Event] = None


def _check_cancellation():
    """Check if cancellation has been requested."""
    return _cancel_event is not None and _cancel_event.is_set()


def _worker_process_runner(func: Callable, args: Tuple, kwargs: dict, output_queue: mp.Queue, cancel_event: mp.Event):
    """
    Run a function in a separate process and communicate results via queue.
    
    Args:
        func: Function to run
        args: Positional arguments
        kwargs: Keyword arguments
        output_queue: Queue for sending results/status back
        cancel_event: Event to signal cancellation
    """
    global _cancel_event
    _cancel_event = cancel_event
    
    try:
        output_queue.put(("status", "Starting operation..."))
        output_queue.put(("progress", 0))
        
        # Add cancel checking function to kwargs
        kwargs["cancel_requested_func"] = _check_cancellation
        
        result = func(*args, **kwargs)
        
        output_queue.put(("progress", 100))
        output_queue.put(("status", "Operation completed!"))
        output_queue.put(("completed", result))
        
    except Exception as e:
        # Check if this is a cancellation exception
        if type(e).__name__ == 'CancellationException':
            output_queue.put(("cancelled", None))
        else:
            error_msg = f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}"
            output_queue.put(("error", error_msg))
    
    finally:
        # Ensure proper cleanup of joblib resources
        # This allows loky backend to clean up memory-mapped files
        try:
            # Clean up any joblib/loky pools
            try:
                from joblib.externals.loky import get_reaper
                reaper = get_reaper()
                if reaper:
                    reaper.shutdown(wait=False)
            except Exception:
                pass
            
            # Force garbage collection to close file handles
            gc.collect()
            
            # Give joblib one last chance to clean up
            time.sleep(0.1)
        except Exception:
            pass


class WorkerThread(QThread):
    """
    Worker that runs long-running operations in a separate process.
    
    Supports true cancellation via process termination.
    Communicates via signals emitted from the main thread.
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
            func: Callable function to run in the process
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
        """
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self._result = None
        self._cancel_requested = False
        self._process: Optional[mp.Process] = None
        self._output_queue: Optional[mp.Queue] = None
        self._cancel_flag: Optional[mp.Event] = None
        self._monitor_timer: Optional[QTimer] = None
        # Ensure this thread doesn't block app shutdown
        self.daemon = True
    
    def request_cancel(self):
        """Request cancellation of the operation."""
        try:
            self._cancel_requested = True
            self.status.emit("Cancelling operation...")
            
            # Set cancel flag first to allow graceful cancellation
            if self._cancel_flag:
                self._cancel_flag.set()
            
            # Terminate the process if it's running
            if self._process and self._process.is_alive():
                try:
                    # Give joblib/loky time to clean up gracefully
                    self._process.terminate()
                    # Wait longer for graceful termination (allows joblib cleanup)
                    self._process.join(timeout=3)
                    if self._process.is_alive():
                        self._process.kill()
                        self._process.join(timeout=1)
                except Exception as e:
                    # Log but don't crash if process termination fails
                    print(f"Error terminating process: {e}")
        except Exception as e:
            print(f"Error in request_cancel: {e}")
    
    def cancel_requested(self) -> bool:
        """Check if cancellation has been requested."""
        return self._cancel_requested
    
    def run(self):
        """Execute the worker function in a separate process."""
        # Create inter-process communication objects
        self._output_queue = mp.Queue()
        self._cancel_flag = mp.Event()
        
        # Create and start the process
        self._process = mp.Process(
            target=_worker_process_runner,
            args=(self.func, self.args, self.kwargs, self._output_queue, self._cancel_flag)
        )
        self._process.start()
        
        # Monitor the process with a timer
        self._monitor_queue()
    
    def _monitor_queue(self):
        """Monitor output queue for messages from the worker process."""
        try:
            while self._process and self._process.is_alive():
                try:
                    # Try to get a message with timeout
                    msg_type, msg_data = self._output_queue.get(timeout=0.1)
                    self._handle_message(msg_type, msg_data)
                except queue.Empty:
                    continue
                except EOFError:
                    # Queue is broken, process probably died
                    break
        except Exception as e:
            if not self._cancel_requested:
                print(f"Error monitoring queue: {e}")
        
        # Check if process was cancelled first
        try:
            if self._cancel_requested and self._process and self._process.exitcode is not None:
                # exitcode is -15 for SIGTERM (terminate) or -9 for SIGKILL (kill)
                if self._process.exitcode < 0:
                    self.cancelled.emit()
                    return
            
            # Process any remaining messages after process exits with timeout to prevent deadlocks
            if self._process:
                cleanup_deadline = time.time() + 2.0  # 2 second timeout for cleanup
                while time.time() < cleanup_deadline:
                    try:
                        msg_type, msg_data = self._output_queue.get(timeout=0.05)
                        self._handle_message(msg_type, msg_data)
                    except queue.Empty:
                        break
                    except EOFError:
                        # Queue is broken
                        break
        except Exception as e:
            if not self._cancel_requested:
                error_msg = f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}"
                self.error.emit(error_msg)
        finally:
            # Ensure queue and process are cleaned up
            try:
                if self._output_queue:
                    self._output_queue.close()
                    self._output_queue.join_thread()
            except Exception:
                pass
            
            # Gracefully clean up process - give it time to finish cleanup
            try:
                if self._process and self._process.is_alive():
                    # First try graceful termination
                    self._process.terminate()
                    # Give process time to clean up resources (especially joblib)
                    self._process.join(timeout=2)
                    # If still alive, force kill
                    if self._process.is_alive():
                        self._process.kill()
                        self._process.join(timeout=1)
            except Exception:
                pass
    
    def _handle_message(self, msg_type: str, msg_data: Any):
        """Handle a message from the worker process."""
        if msg_type == "progress":
            self.progress.emit(msg_data)
        elif msg_type == "status":
            self.status.emit(msg_data)
        elif msg_type == "completed":
            self._result = msg_data
            self.completed.emit(msg_data)
        elif msg_type == "error":
            self.error.emit(msg_data)
        elif msg_type == "cancelled":
            self.cancelled.emit()
    
    def get_result(self):
        """Get the result from the completed operation."""
        return self._result
