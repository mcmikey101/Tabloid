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
    QMessageBox,
    QScrollArea,
    QApplication,
    QMenu
)

from PySide6.QtCore import Qt

from ui.widgets.dataset_list import DatasetListWidget
from ui.widgets.version_tree import VersionTreeWidget
from ui.widgets.data_table import DataTableWidget
from ui.widgets.column_stats import ColumnStatsWidget
from ui.widgets.distribution_plot import DistributionPlotWidget
from ui.dialogs.operations_dialog import OperationsDialog
from ui.dialogs.synthesis_dialog import SynthesisDialog
from ui.dialogs.compare_plots_dialog import ComparisonPlotsDialog

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

        # Dataset list with delete button
        dataset_widget = self._create_dataset_section()
        splitter.addWidget(dataset_widget)

        center_widget = self._create_center_panel()
        splitter.addWidget(center_widget)

        # Version tree with delete button
        version_widget = self._create_version_section()
        splitter.addWidget(version_widget)

        splitter.setSizes([1, 2, 1])  # Proportional: 1:2:1 ratio for responsive scaling
        splitter.setCollapsible(0, True)  # Allow sidebar collapse on small screens
        splitter.setCollapsible(2, True)  # Allow version tree collapse on small screens

        root_layout.addWidget(splitter)

    def _create_top_bar(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        self.dataset_label = QLabel("Dataset: None")
        self.version_label = QLabel("Version: None")
        self.dataset_label.setMaximumWidth(300)
        self.version_label.setMaximumWidth(300)

        layout.addWidget(self.dataset_label)
        layout.addWidget(self.version_label)
        
        # Dataset shape indicator (rows x columns)
        self.shape_label = QLabel("")
        self.shape_label.setStyleSheet("""
            color: #999999;
            font-size: 10px;
            padding: 0px 8px;
        """)
        layout.addWidget(self.shape_label)
        
        layout.addStretch()

        # ===== PRIMARY ACTION BUTTONS =====
        self.operations_btn = QPushButton("Preprocess")
        self.operations_btn.setStyleSheet("""
            QPushButton {
                background-color: #5b7cfa;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4c63d2;
            }
        """)
        
        self.train_model_btn = QPushButton("Train Model")
        self.train_model_btn.setStyleSheet("""
            QPushButton {
                background-color: #5b7cfa;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4c63d2;
            }
        """)
        
        layout.addWidget(self.operations_btn)
        layout.addWidget(self.train_model_btn)
        
        # Visual separator
        separator1 = QLabel("|")
        separator1.setStyleSheet("color: #3a3d4a; padding: 0px 4px;")
        layout.addWidget(separator1)
        
        # ===== SECONDARY ACTION BUTTONS =====
        self.synthesize_btn = QPushButton("Synthesize")
        self.synthesize_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3d4a;
                color: #e0e0e0;
                border: 1px solid #3a3d4a;
                padding: 6px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4a4d5a;
                border: 1px solid #5b7cfa;
            }
        """)
        
        self.export_btn = QPushButton("Export")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3d4a;
                color: #e0e0e0;
                border: 1px solid #3a3d4a;
                padding: 6px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4a4d5a;
                border: 1px solid #5b7cfa;
            }
        """)
        
        self.compare_plots_btn = QPushButton("Compare")
        self.compare_plots_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3d4a;
                color: #e0e0e0;
                border: 1px solid #3a3d4a;
                padding: 6px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4a4d5a;
                border: 1px solid #5b7cfa;
            }
        """)
        
        layout.addWidget(self.synthesize_btn)
        layout.addWidget(self.export_btn)
        layout.addWidget(self.compare_plots_btn)

        return layout

    def _create_center_panel(self):
        center = QWidget()
        layout = QVBoxLayout(center)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.data_table = DataTableWidget()
        self.column_stats = ColumnStatsWidget()
        self.distribution_plot = DistributionPlotWidget()

        # Create scroll area for proper overflow handling on small screens
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background-color: #262738; border: none; }")
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(4)
        
        scroll_layout.addWidget(self.data_table)
        scroll_layout.addWidget(self.column_stats)
        scroll_layout.addWidget(self.distribution_plot)
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        return center

    def _create_dataset_section(self):
        """Create dataset list section with delete button."""
        container = QWidget()
        layout = QVBoxLayout(container)

        self.dataset_list = DatasetListWidget()
        layout.addWidget(self.dataset_list)

        self.delete_dataset_btn = QPushButton("Delete Dataset")
        layout.addWidget(self.delete_dataset_btn)

        return container

    def _create_version_section(self):
        """Create version tree section with delete button."""
        container = QWidget()
        layout = QVBoxLayout(container)

        self.version_tree = VersionTreeWidget()
        layout.addWidget(self.version_tree)

        self.delete_version_btn = QPushButton("Delete Version")
        layout.addWidget(self.delete_version_btn)

        return container

    # -----------------------------------------------------
    # Signals
    # -----------------------------------------------------

    def _connect_signals(self):

        self.dataset_list.dataset_selected.connect(self.load_dataset)
        self.dataset_list.add_dataset_requested.connect(self.add_dataset)

        self.version_tree.version_selected.connect(self.load_version)

        self.data_table.column_selected.connect(self.update_column_stats)
        self.data_table.column_selected.connect(self.distribution_plot.plot_column)

        self.operations_btn.clicked.connect(self.open_operations_dialog)
        self.synthesize_btn.clicked.connect(self.open_synthesis_dialog)
        self.export_btn.clicked.connect(self.export_version)
        self.train_model_btn.clicked.connect(self.open_train_model)
        self.compare_plots_btn.clicked.connect(self.open_compare_plots_dialog)
        self.delete_version_btn.clicked.connect(self.delete_current_version)
        self.delete_dataset_btn.clicked.connect(self.delete_current_dataset)

    def export_version(self):
        # Ask for format
        formats = ["CSV", "Excel", "Parquet", "JSON"]
        format_choice, ok = QInputDialog.getItem(
            self,
            "Export Format",
            "Select export format:",
            formats,
            0,
            False
        )

        if not ok:
            return

        # Get file path
        file_dialog_filters = {
            "CSV": "CSV files (*.csv)",
            "Excel": "Excel files (*.xlsx)",
            "Parquet": "Parquet files (*.parquet)",
            "JSON": "JSON files (*.json)"
        }

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Dataset",
            f"{self.current_dataset}_{self.current_version}",
            file_dialog_filters[format_choice]
        )

        if not file_path:
            return

        try:
            if format_choice == "CSV":
                self.current_df.to_csv(file_path, index=False)
            elif format_choice == "Excel":
                self.current_df.to_excel(file_path, index=False)
            elif format_choice == "Parquet":
                self.current_df.to_parquet(file_path, index=False)
            elif format_choice == "JSON":
                self.current_df.to_json(file_path, orient="records", indent=2)
            
            QMessageBox.information(
                self,
                "Success",
                f"Dataset exported to {file_path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export: {str(e)}"
            )

    def open_train_model(self):
        """Open ML Lab page with current dataset and version pre-selected."""
        if not self.current_dataset or not self.current_version:
            QMessageBox.warning(
                self,
                "Warning",
                "Please load a dataset and version first."
            )
            return

        main_window = self.window()
        if not hasattr(main_window, 'pages'):
            QMessageBox.critical(
                self,
                "Error",
                "Could not access ML Lab page."
            )
            return

        ml_lab_page = main_window.pages.widget(2)

        try:
            ml_lab_page.dataset_combo.setCurrentText(self.current_dataset)

            ml_lab_page.version_combo.blockSignals(True)
            ml_lab_page._on_dataset_changed(self.current_dataset)
            ml_lab_page.version_combo.setCurrentText(self.current_version)
            ml_lab_page.version_combo.blockSignals(False)

            ml_lab_page._on_version_changed(self.current_version)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Warning",
                f"Could not pre-select dataset/version: {str(e)}"
            )

        main_window.pages.setCurrentIndex(2)

    def open_synthesis_dialog(self):
        """Open the operations builder dialog."""
        if not self.current_dataset or self.current_df is None:
            QMessageBox.warning(
                self,
                "Warning",
                "Please load a dataset and version first."
            )
            return

        dialog = SynthesisDialog(self)
        dialog.set_dataframe(self.current_df)
        dialog.set_source_info(self.current_dataset, self.current_version)

        if dialog.exec() == SynthesisDialog.Accepted:
            result_df, result_config = dialog.get_results()
            if result_df is None:
                return
            
            # Ask for version name
            version_name, ok = QInputDialog.getText(
                self,
                "Save Version",
                "Enter new version name:"
            )
            if not ok or not version_name:
                return
            
            try:
                # Save as new version
                self.version_manager.create_version(
                    dataset_name=self.current_dataset,
                    version_name=version_name,
                    df=result_df,
                    parent_version=self.current_version,
                    operation="synthesis",
                    config=result_config
                )
                # Reload and display
                self.load_dataset(self.current_dataset)
                self._refresh_ml_lab_versions()
                self.version_tree.select_version(version_name)
                self.load_version(version_name)
                QMessageBox.information(
                    self,
                    "Success",
                    f"Synthetic version '{version_name}' created!"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to save version: {str(e)}"
                )

    

    def open_compare_plots_dialog(self):
        """Open the comparison plots dialog."""
        if self.current_dataset is None:
            QMessageBox.warning(
                self,
                "Warning",
                "Please load a dataset first."
            )
            return

        dialog = ComparisonPlotsDialog(
            self.version_manager,
            self.file_store,
            self.current_dataset,
            self
        )
        dialog.exec()

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

        self.version_tree.load_versions(version_graph, self.version_manager, dataset_name)

        # Automatically select the raw version if it exists
        if "raw" in version_graph:
            self.version_tree.select_version("raw")
            self.load_version("raw")

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
        
        # Update dataset shape display (rows x columns)
        rows, cols = df.shape
        self.shape_label.setText(f"Shape: {rows} rows × {cols} columns")

        self.data_table.load_dataframe(df)
        self.distribution_plot.load_dataframe(
            df, 
            dataset_name=self.current_dataset,
            version_name=version_name
        )

    # -----------------------------------------------------
    # Column Statistics
    # -----------------------------------------------------

    def update_column_stats(self, column_name):

        if self.current_df is None:
            return

        metadata = derive_metadata(self.current_df)

        stats = metadata["columns"].get(column_name, {})
        # Add the column name to stats so display_stats can use it
        stats["name"] = column_name

        self.column_stats.display_stats(stats)

    def _refresh_ml_lab_versions(self):
        """Refresh the version combo in ML Lab page after a new version is created."""
        try:
            main_window = self.window()
            if hasattr(main_window, 'pages'):
                ml_lab_page = main_window.pages.widget(2)
                if ml_lab_page and hasattr(ml_lab_page, '_on_dataset_changed'):
                    current_ml_dataset = ml_lab_page.dataset_combo.currentText()
                    if current_ml_dataset == self.current_dataset:
                        ml_lab_page._on_dataset_changed(self.current_dataset)
        except Exception:
            pass

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

    # -----------------------------------------------------
    # Operations
    # -----------------------------------------------------

    def open_operations_dialog(self):
        """Open the operations builder dialog."""
        if not self.current_dataset or self.current_df is None:
            QMessageBox.warning(
                self,
                "Warning",
                "Please load a dataset and version first."
            )
            return

        dialog = OperationsDialog(self)
        dialog.set_dataframe(self.current_df)

        if dialog.exec() == OperationsDialog.Accepted:
            result_df, result_config = dialog.get_results()

            if result_df is None:
                return

            # Ask for version name
            version_name, ok = QInputDialog.getText(
                self,
                "Save Version",
                "Enter new version name:"
            )

            if not ok or not version_name:
                return

            try:
                # Save as new version
                self.version_manager.create_version(
                    dataset_name=self.current_dataset,
                    version_name=version_name,
                    df=result_df,
                    parent_version=self.current_version,
                    operation="operations_sequence",
                    config=result_config
                )

                # Reload version tree
                self.load_dataset(self.current_dataset)
                self._refresh_ml_lab_versions()

                # Auto-select the new version
                self.version_tree.select_version(version_name)
                self.load_version(version_name)

                QMessageBox.information(
                    self,
                    "Success",
                    f"Version '{version_name}' created successfully!"
                )

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to save version: {str(e)}"
                )

    # -----------------------------------------------------
    # Delete Operations
    # -----------------------------------------------------

    def delete_current_version(self):
        """Delete the current version."""
        if not self.current_dataset or not self.current_version:
            QMessageBox.warning(
                self,
                "Warning",
                "Please select a version to delete."
            )
            return

        if self.current_version == "raw":
            QMessageBox.warning(
                self,
                "Warning",
                "Cannot delete the 'raw' version."
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete version '{self.current_version}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:

            temp_current_version = self.current_version

            self.version_manager.delete_version(
                self.current_dataset,
                self.current_version
            )

            # Reload version tree
            self.load_dataset(self.current_dataset)

            QMessageBox.information(
                self,
                "Success",
                f"Version '{temp_current_version}' deleted successfully!"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to delete version: {str(e)}"
            )

    def delete_current_dataset(self):
        """Delete the current dataset."""
        if not self.current_dataset:
            QMessageBox.warning(
                self,
                "Warning",
                "Please select a dataset to delete."
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete dataset '{self.current_dataset}' and all its versions?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            dataset_name = self.current_dataset
            self.dataset_manager.delete_dataset(dataset_name)

            # Reset current dataset
            self.current_dataset = None
            self.current_version = None
            self.current_df = None

            # Reload datasets
            self._load_datasets()

            self.dataset_label.setText("Dataset: None")
            self.version_label.setText("Version: None")
            self.data_table.table.setRowCount(0)
            self.distribution_plot.figure.clear()
            self.distribution_plot.canvas.draw()
            self.version_tree.tree.clear()

            QMessageBox.information(
                self,
                "Success",
                f"Dataset '{dataset_name}' deleted successfully!"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to delete dataset: {str(e)}"
            )