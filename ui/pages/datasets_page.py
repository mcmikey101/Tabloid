# ui/pages/datasets_page.py

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QPushButton,
    QLabel
)
from PySide6.QtCore import Qt

from ui.widgets.dataset_list import DatasetListWidget
from ui.widgets.version_tree import VersionTreeWidget
from ui.widgets.data_table import DataTableWidget
from ui.widgets.column_stats import ColumnStatsWidget
from ui.widgets.distribution_plot import DistributionPlotWidget


class DatasetsPage(QWidget):
    """
    Main workspace for dataset exploration and version management.
    Layout:

    ---------------------------------------------------------
    Top Bar: [Dataset] [Version]             [Operations][Synthesize]
    ---------------------------------------------------------
    Left Panel      | Center Panel           | Right Panel
    Dataset List    | Data Table             | Version Tree
                    | Column Stats           |
                    | Distribution Plot      |
    ---------------------------------------------------------
    """

    def __init__(self):
        super().__init__()
        self._build_ui()

    # -----------------------------------------------------
    # UI Construction
    # -----------------------------------------------------

    def _build_ui(self):
        root_layout = QVBoxLayout(self)

        # Top controls
        top_bar = self._create_top_bar()
        root_layout.addLayout(top_bar)

        # Main workspace
        splitter = QSplitter(Qt.Horizontal)

        # Left: dataset list
        self.dataset_list = DatasetListWidget()
        splitter.addWidget(self.dataset_list)

        # Center: data table + analytics
        center_widget = self._create_center_panel()
        splitter.addWidget(center_widget)

        # Right: version tree
        self.version_tree = VersionTreeWidget()
        splitter.addWidget(self.version_tree)

        splitter.setSizes([200, 800, 300])

        root_layout.addWidget(splitter)

    def _create_top_bar(self):
        layout = QHBoxLayout()

        self.dataset_label = QLabel("Dataset: None")
        self.version_label = QLabel("Version: None")

        layout.addWidget(self.dataset_label)
        layout.addWidget(self.version_label)

        layout.addStretch()

        self.operations_btn = QPushButton("Operations")
        self.synthesize_btn = QPushButton("Synthesize")

        layout.addWidget(self.operations_btn)
        layout.addWidget(self.synthesize_btn)

        return layout

    def _create_center_panel(self):
        center = QWidget()
        layout = QVBoxLayout(center)

        # Data table
        self.data_table = DataTableWidget()

        # Column statistics
        self.column_stats = ColumnStatsWidget()

        # Distribution plot
        self.distribution_plot = DistributionPlotWidget()

        layout.addWidget(self.data_table)
        layout.addWidget(self.column_stats)
        layout.addWidget(self.distribution_plot)

        return center

    # -----------------------------------------------------
    # Future interaction hooks
    # -----------------------------------------------------

    def load_dataset(self, dataset_name: str):
        """Load dataset into UI components."""
        pass

    def load_version(self, version_name: str):
        """Load selected dataset version."""
        pass

    def apply_operations(self):
        """Open preprocessing operations dialog."""
        pass

    def run_synthesis(self):
        """Open synthesis configuration dialog."""
        pass