# ui/main_window.py

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QStackedWidget,
    QSizePolicy
)
from PySide6.QtCore import Qt

from ui.pages.datasets_page import DatasetsPage
from ui.pages.experiments_page import ExperimentsPage
from ui.pages.ml_lab_page import MLLabPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Tabloid")
        self.resize(1400, 900)

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
        sidebar.setFixedWidth(200)

        layout = QVBoxLayout(sidebar)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.datasets_btn = QPushButton("Datasets")
        self.experiments_btn = QPushButton("Experiments")
        self.ml_lab_btn = QPushButton("ML Lab")

        self.datasets_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.experiments_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.ml_lab_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.datasets_btn.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        self.experiments_btn.clicked.connect(lambda: self.pages.setCurrentIndex(1))
        self.ml_lab_btn.clicked.connect(lambda: self.pages.setCurrentIndex(2))

        layout.addWidget(self.datasets_btn)
        layout.addWidget(self.experiments_btn)
        layout.addWidget(self.ml_lab_btn)
        layout.addStretch()

        return sidebar