import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QFont, QFontDatabase
from ui.main_window import MainWindow

import os
import multiprocessing


def load_stylesheet(app):
    """Load the application stylesheet from file."""
    style_file = os.path.join(os.path.dirname(__file__), 'ui/style.qss')
    if os.path.exists(style_file):
        with open(style_file, 'r') as f:
            stylesheet = f.read()
            app.setStyleSheet(stylesheet)


def setup_fonts():
    """Setup application fonts including JetBrains Mono from Google Fonts."""
    try:
        # Try to load JetBrains Mono from system or embedded location
        # This assumes the font is installed on the system
        # Fallback is handled in the stylesheet
        pass
    except Exception as e:
        print(f"Note: Could not load custom fonts: {e}")


def main():
    # Set multiprocessing start method for consistent cross-platform behavior
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        # Ignore if already set
        pass
    
    app = QApplication(sys.argv)

    icon_path = os.path.join(os.path.dirname(__file__), 'assets/tabloid_icon.png')

    # Set the window icon
    app.setWindowIcon(QIcon(icon_path))

    # Setup fonts and stylesheet
    setup_fonts()
    load_stylesheet(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()