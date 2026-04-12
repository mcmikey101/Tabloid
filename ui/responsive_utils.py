"""
Utility functions for responsive UI design in PySide6 applications.
Handles screen-aware sizing, centering, and scaling.
"""

from PySide6.QtWidgets import QApplication, QMainWindow, QDialog
from PySide6.QtCore import QSize


def set_responsive_window_size(window: QMainWindow, 
                              default_width_percent: float = 0.9,
                              default_height_percent: float = 0.9,
                              min_width: int = 960,
                              min_height: int = 600) -> None:
    """
    Set responsive window size based on screen geometry.
    
    Args:
        window: QMainWindow or QDialog to resize
        default_width_percent: Percentage of screen width to use (0.0-1.0)
        default_height_percent: Percentage of screen height to use (0.0-1.0)
        min_width: Minimum window width
        min_height: Minimum window height
    """
    screen = QApplication.primaryScreen().availableGeometry()
    
    width = max(min_width, int(screen.width() * default_width_percent))
    height = max(min_height, int(screen.height() * default_height_percent))
    
    window.resize(width, height)
    window.setMinimumSize(min_width, min_height)
    
    # Center window on screen
    center_window_on_screen(window)


def set_responsive_dialog_size(dialog: QDialog,
                              default_width_percent: float = 0.6,
                              default_height_percent: float = 0.6,
                              min_width: int = 400,
                              min_height: int = 300) -> None:
    """
    Set responsive dialog size based on screen geometry.
    
    Args:
        dialog: QDialog to resize
        default_width_percent: Percentage of screen width to use (0.0-1.0)
        default_height_percent: Percentage of screen height to use (0.0-1.0)
        min_width: Minimum dialog width
        min_height: Minimum dialog height
    """
    screen = QApplication.primaryScreen().availableGeometry()
    
    width = max(min_width, int(screen.width() * default_width_percent))
    height = max(min_height, int(screen.height() * default_height_percent))
    
    dialog.resize(width, height)
    dialog.setMinimumSize(min_width, min_height)
    
    # Center dialog on screen
    center_window_on_screen(dialog)


def center_window_on_screen(window) -> None:
    """
    Center window on current screen (handles multi-monitor setups).
    
    Args:
        window: QMainWindow or QDialog to center
    """
    screen = QApplication.primaryScreen().availableGeometry()
    geometry = window.frameGeometry()
    geometry.moveCenter(screen.center())
    window.move(geometry.topLeft())


def get_responsive_font_size(base_size: int = 12) -> int:
    """
    Get DPI-aware font size.
    
    Args:
        base_size: Base font size (typically 12pt for 96 DPI)
        
    Returns:
        Scaled font size in points
    """
    dpi = QApplication.primaryScreen().logicalDotsPerInch()
    # Typical DPI is 96; scale relative to that
    return max(8, int(base_size * dpi / 96))


def get_responsive_width(percent: float, min_value: int = 100) -> int:
    """
    Get width as percentage of screen, with minimum.
    
    Args:
        percent: Percentage of screen width (0.0-1.0)
        min_value: Minimum width in pixels
        
    Returns:
        Calculated width in pixels
    """
    screen = QApplication.primaryScreen().availableGeometry()
    return max(min_value, int(screen.width() * percent))


def get_responsive_height(percent: float, min_value: int = 100) -> int:
    """
    Get height as percentage of screen, with minimum.
    
    Args:
        percent: Percentage of screen height (0.0-1.0)
        min_value: Minimum height in pixels
        
    Returns:
        Calculated height in pixels
    """
    screen = QApplication.primaryScreen().availableGeometry()
    return max(min_value, int(screen.height() * percent))
