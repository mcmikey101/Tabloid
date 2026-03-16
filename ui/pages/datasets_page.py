# ui/pages/datasets_page.py

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QPushButton,
    QLabel,
    QFileDialog,
    QInputDialog,
    QMessageBox
)

from PySide6.QtCore import Qt

from ui.widgets.dataset_list import DatasetListWidget
from ui.widgets.version_tree import VersionTreeWidget
from ui.widgets.data_table import DataTableWidget
from ui.widgets.column_stats import ColumnStatsWidget
from ui.widgets.distribution_plot import DistributionPlotWidget

from storage.file_store import FileStore
from core.dataset_manager import DatasetManager
from core.version_manager import VersionManager
from core.metadata import derive_metadata


class DatasetsPage(QWidget):

    def __init__(self):
        super().__init__()
        
        self.file_store = FileStore()
        self.version_manager = VersionManager(file_store=self.file_store)
        self.dataset_manager = DatasetManager(version_manager=self.version_manager, file_store=self.file_store)

        self.current_dataset = None
        self.current_version = None
        self.current_df = None

        self._build_ui()
        self._connect_signals()
        self._load_datasets()

    # -----------------------------------------------------
    # UI
    # -----------------------------------------------------

    def _build_ui(self):
        root_layout = QVBoxLayout(self)

        top_bar = self._create_top_bar()
        root_layout.addLayout(top_bar)

        splitter = QSplitter(Qt.Horizontal)

        self.dataset_list = DatasetListWidget()
        splitter.addWidget(self.dataset_list)

        center_widget = self._create_center_panel()
        splitter.addWidget(center_widget)

        self.version_tree = VersionTreeWidget()
        splitter.addWidget(self.version_tree)

        splitter.setSizes([250, 900, 300])

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

        self.data_table = DataTableWidget()
        self.column_stats = ColumnStatsWidget()
        self.distribution_plot = DistributionPlotWidget()

        layout.addWidget(self.data_table)
        layout.addWidget(self.column_stats)
        layout.addWidget(self.distribution_plot)

        return center

    # -----------------------------------------------------
    # Signals
    # -----------------------------------------------------

    def _connect_signals(self):

        self.dataset_list.dataset_selected.connect(self.load_dataset)
        self.dataset_list.add_dataset_requested.connect(self.add_dataset)

        self.version_tree.version_selected.connect(self.load_version)

        self.data_table.column_selected.connect(self.update_column_stats)

    # -----------------------------------------------------
    # Dataset Loading
    # -----------------------------------------------------

    def _load_datasets(self):

        datasets = self.dataset_manager.list_datasets()
        self.dataset_list.set_datasets(datasets)

    def load_dataset(self, dataset_name):

        self.current_dataset = dataset_name
        self.dataset_label.setText(f"Dataset: {dataset_name}")

        version_graph = self.version_manager.get_version_graph(dataset_name)

        self.version_tree.load_versions(version_graph)

    # -----------------------------------------------------
    # Version Loading
    # -----------------------------------------------------

    def load_version(self, version_name):

        if not self.current_dataset:
            return

        df = self.dataset_manager.load_version(
            dataset_name=self.current_dataset,
            version_name=version_name
        )

        self.current_version = version_name
        self.current_df = df

        self.version_label.setText(f"Version: {version_name}")

        self.data_table.load_dataframe(df)
        self.distribution_plot.load_dataframe(df)

    # -----------------------------------------------------
    # Column Statistics
    # -----------------------------------------------------

    def update_column_stats(self, column_name):

        if self.current_df is None:
            return

        metadata = derive_metadata(self.current_df)

        stats = metadata["columns"].get(column_name, {})

        self.column_stats.display_stats(stats)

    # -----------------------------------------------------
    # Dataset Import
    # -----------------------------------------------------

    def add_dataset(self):

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select dataset file",
            "",
            "Data files (*.csv *.xlsx)"
        )

        if not file_path:
            return

        dataset_name, ok = QInputDialog.getText(
            self,
            "Dataset Name",
            "Enter dataset name:"
        )

        if not ok or not dataset_name:
            return

        try:

            self.dataset_manager.create_dataset(
                dataset_name=dataset_name,
                file_path=file_path
            )

            self._load_datasets()

        except Exception as e:

            QMessageBox.critical(
                self,
                "Import Error",
                str(e)
            )