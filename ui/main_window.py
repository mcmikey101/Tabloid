# ui/main_window.py

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QStackedWidget,
    QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from ui.pages.datasets_page import DatasetsPage
from ui.pages.experiments_page import ExperimentsPage
from ui.pages.ml_lab_page import MLLabPage

import os


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Tabloid")
        
        # Set responsive window size based on screen geometry
        screen = QApplication.primaryScreen().availableGeometry()
        default_width = min(1200, int(screen.width() * 0.9))
        default_height = min(800, int(screen.height() * 0.9))
        
        self.resize(default_width, default_height)
        self.setMinimumSize(960, 600)  # Minimum usable size
        
        # Center window on screen
        geometry = self.frameGeometry()
        geometry.moveCenter(screen.center())
        self.move(geometry.topLeft())

        # Set window icon for taskbar
        icon_path = os.path.join(os.path.dirname(__file__), '../assets/tabloid_icon.png')
        self.setWindowIcon(QIcon(icon_path))

        self._build_ui()

    def _build_ui(self):
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Top navbar navigation
        navbar = self._create_navbar()
        root_layout.addLayout(navbar)

        # Page stack
        self.pages = QStackedWidget()
        self.pages.addWidget(DatasetsPage())
        self.pages.addWidget(ExperimentsPage())
        self.pages.addWidget(MLLabPage())

        root_layout.addWidget(self.pages)

        self.setCentralWidget(root)

    def _create_navbar(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # Navigation buttons
        self.datasets_btn = QPushButton("Datasets")
        self.experiments_btn = QPushButton("Experiments")
        self.ml_lab_btn = QPushButton("ML Lab")

        for btn in [self.datasets_btn, self.experiments_btn, self.ml_lab_btn]:
            btn.setFixedHeight(32)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3a3d4a;
                    color: #e0e0e0;
                    border: 1px solid #3a3d4a;
                    padding: 4px 16px;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #4a4d5a;
                    border: 1px solid #5b7cfa;
                }
                QPushButton:pressed {
                    background-color: #5b7cfa;
                    color: white;
                }
            """)
            layout.addWidget(btn)

        self.datasets_btn.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        self.experiments_btn.clicked.connect(lambda: self.pages.setCurrentIndex(1))
        self.ml_lab_btn.clicked.connect(lambda: self.pages.setCurrentIndex(2))

        layout.addStretch()
        return layout