import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

from PySide6.QtGui import QIcon
import os


def main():
    app = QApplication(sys.argv)

    icon_path = os.path.join(os.path.dirname(__file__), 'assets/tabloid_icon.png')

    # Set the window icon
    app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()