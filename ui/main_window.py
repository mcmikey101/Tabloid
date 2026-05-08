# ui/main_window.py

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QStackedWidget,
    QSizePolicy,
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
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # Sidebar navigation
        sidebar = self._create_sidebar()

        # Page stack
        self.pages = QStackedWidget()
        self.pages.addWidget(DatasetsPage())
        self.pages.addWidget(ExperimentsPage())
        self.pages.addWidget(MLLabPage())

        root_layout.addWidget(sidebar)
        root_layout.addWidget(self.pages)

        self.setCentralWidget(root)

    def _create_sidebar(self):
        sidebar = QWidget()
        self.sidebar_expanded = True

        self.sidebar_expanded_width = 200
        self.sidebar_collapsed_width = 60

        sidebar.setMinimumWidth(self.sidebar_collapsed_width)
        sidebar.setMaximumWidth(self.sidebar_expanded_width)
        sidebar.setFixedWidth(self.sidebar_expanded_width)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Toggle button
        self.toggle_btn = QPushButton("☰")
        self.toggle_btn.setFixedHeight(40)
        self.toggle_btn.clicked.connect(self._toggle_sidebar)
        layout.addWidget(self.toggle_btn)

        # Navigation buttons
        self.datasets_btn = QPushButton("Datasets")
        self.experiments_btn = QPushButton("Experiments")
        self.ml_lab_btn = QPushButton("ML Lab")

        for btn in [self.datasets_btn, self.experiments_btn, self.ml_lab_btn]:
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setFixedHeight(40)
            layout.addWidget(btn)

        self.datasets_btn.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        self.experiments_btn.clicked.connect(lambda: self.pages.setCurrentIndex(1))
        self.ml_lab_btn.clicked.connect(lambda: self.pages.setCurrentIndex(2))

        layout.addStretch()

        return sidebar


    def _toggle_sidebar(self):
        if self.sidebar_expanded:
            self.sidebar_expanded = False
            self.sender().parent().setFixedWidth(self.sidebar_collapsed_width)

            # Collapse: hide text
            self.datasets_btn.setText("")
            self.experiments_btn.setText("")
            self.ml_lab_btn.setText("")
        else:
            self.sidebar_expanded = True
            self.sender().parent().setFixedWidth(self.sidebar_expanded_width)

            # Expand: restore text
            self.datasets_btn.setText("Datasets")
            self.experiments_btn.setText("Experiments")
            self.ml_lab_btn.setText("ML Lab")