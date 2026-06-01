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

        splitter.setSizes([1, 3, 1])  # Proportional: 1:3:1 ratio (datasets:data:versions)
        splitter.setCollapsible(0, True)  # Allow sidebar collapse on small screens
        splitter.setCollapsible(2, True)  # Allow version tree collapse on small screens

        root_layout.addWidget(splitter)

    def _create_top_bar(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        self.dataset_label = QLabel("Датасет: нет")
        self.version_label = QLabel("Версия: нет")
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
        self.operations_btn = QPushButton("Предобработка")
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
        
        self.train_model_btn = QPushButton("Обучить модель")
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
        self.synthesize_btn = QPushButton("Синтез")
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
        
        self.export_btn = QPushButton("Экспорт")
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
        
        self.compare_plots_btn = QPushButton("Сравнить")
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
        layout.setSpacing(0)

        self.data_table = DataTableWidget()
        self.column_stats = ColumnStatsWidget()
        self.distribution_plot = DistributionPlotWidget()

        # Create splitter for resizable stats/distribution panel
        stats_detail_splitter = QSplitter(Qt.Vertical)
        stats_detail_splitter.addWidget(self.column_stats)
        stats_detail_splitter.addWidget(self.distribution_plot)
        stats_detail_splitter.setSizes([1, 1])  # Equal height by default
        stats_detail_splitter.setCollapsible(0, True)
        stats_detail_splitter.setCollapsible(1, True)
        # Style the splitter handle to show a thin line indicator
        stats_detail_splitter.setHandleWidth(1)
        stats_detail_splitter.setStyleSheet("""
            QSplitter::handle:vertical {
                background-color: #3a3d4a;
                border: none;
                margin: 2px 0px;
                padding: 0px;
            }
            QSplitter::handle:vertical:hover {
                background-color: #5b7cfa;
            }
        """)

        # Create splitter for data table and stats panel
        stats_splitter = QSplitter(Qt.Vertical)
        stats_splitter.addWidget(self.data_table)
        stats_splitter.addWidget(stats_detail_splitter)
        stats_splitter.setSizes([2, 1])  # Data table 2 parts, stats 1 part
        stats_splitter.setCollapsible(0, False)
        stats_splitter.setCollapsible(1, True)
        # Style the main splitter handle
        stats_splitter.setHandleWidth(1)
        stats_splitter.setStyleSheet("""
            QSplitter::handle:vertical {
                background-color: #3a3d4a;
                border: none;
                margin: 2px 0px;
                padding: 0px;
            }
            QSplitter::handle:vertical:hover {
                background-color: #5b7cfa;
            }
        """)

        layout.addWidget(stats_splitter)

        return center

    def _create_dataset_section(self):
        """Create dataset list section with delete button."""
        container = QWidget()
        layout = QVBoxLayout(container)

        self.dataset_list = DatasetListWidget()
        layout.addWidget(self.dataset_list)

        self.delete_dataset_btn = QPushButton("Удалить датасет")
        layout.addWidget(self.delete_dataset_btn)

        return container

    def _create_version_section(self):
        """Create version tree section with delete button."""
        container = QWidget()
        layout = QVBoxLayout(container)

        self.version_tree = VersionTreeWidget()
        layout.addWidget(self.version_tree)

        self.delete_version_btn = QPushButton("Удалить версию")
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
            "Формат экспорта",
            "Выберите формат экспорта:",
            formats,
            0,
            False
        )

        if not ok:
            return

        # Get file path
        file_dialog_filters = {
            "CSV": "CSV-файлы (*.csv)",
            "Excel": "Excel-файлы (*.xlsx)",
            "Parquet": "Parquet-файлы (*.parquet)",
            "JSON": "JSON-файлы (*.json)"
        }

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт датасета",
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
                "Успех",
                f"Датасет экспортирован в {file_path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка экспорта",
                f"Не удалось экспортировать: {str(e)}"
            )

    def open_train_model(self):
        """Open ML Lab page with current dataset and version pre-selected."""
        if not self.current_dataset or not self.current_version:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Сначала загрузите датасет и версию."
            )
            return

        main_window = self.window()
        if not hasattr(main_window, 'pages'):
            QMessageBox.critical(
                self,
                "Ошибка",
                "Не удалось открыть страницу ML-лаборатории."
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
                "Предупреждение",
                f"Не удалось заранее выбрать датасет/версию: {str(e)}"
            )

        main_window.pages.setCurrentIndex(2)

    def open_synthesis_dialog(self):
        """Open the operations builder dialog."""
        if not self.current_dataset or self.current_df is None:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Сначала загрузите датасет и версию."
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
                "Сохранить версию",
                "Введите имя новой версии:"
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
                    "Успех",
                    f"Синтетическая версия '{version_name}' создана!"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось сохранить версию: {str(e)}"
                )

    

    def open_compare_plots_dialog(self):
        """Open the comparison plots dialog."""
        if self.current_dataset is None:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Сначала загрузите датасет."
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
        self.dataset_label.setText(f"Датасет: {dataset_name}")

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

        self.version_label.setText(f"Версия: {version_name}")
        
        # Update dataset shape display (rows x columns)
        rows, cols = df.shape
        self.shape_label.setText(f"Размер: {rows} строк × {cols} столбцов")

        self.data_table.load_dataframe(df)
        self.distribution_plot.load_dataframe(
            df, 
            dataset_name=self.current_dataset,
            version_name=version_name
        )

        self.data_table.table.clearSelection()
        self.column_stats.display_stats({})
        self.distribution_plot.figure.clear()
        self.distribution_plot.canvas.draw()
        self.distribution_plot.column_info_label.setText("Выберите столбец для визуализации")

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
            "Выберите файл датасета",
            "",
            "Файлы данных (*.csv *.xlsx)"
        )

        if not file_path:
            return

        dataset_name, ok = QInputDialog.getText(
            self,
            "Название датасета",
            "Введите название датасета:"
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
                "Ошибка импорта",
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
                "Предупреждение",
                "Сначала загрузите датасет и версию."
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
                "Сохранить версию",
                "Введите имя новой версии:"
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
                    "Успех",
                    f"Версия '{version_name}' успешно создана!"
                )

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось сохранить версию: {str(e)}"
                )

    # -----------------------------------------------------
    # Delete Operations
    # -----------------------------------------------------

    def delete_current_version(self):
        """Delete the current version."""
        if not self.current_dataset or not self.current_version:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Выберите версию для удаления."
            )
            return

        if self.current_version == "raw":
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Нельзя удалить версию 'raw'."
            )
            return

        reply = QMessageBox.question(
            self,
            "Подтвердите удаление",
            f"Удалить версию '{self.current_version}'?",
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
                "Успех",
                f"Версия '{temp_current_version}' успешно удалена!"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось удалить версию: {str(e)}"
            )

    def delete_current_dataset(self):
        """Delete the current dataset."""
        if not self.current_dataset:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Выберите датасет для удаления."
            )
            return

        reply = QMessageBox.question(
            self,
            "Подтвердите удаление",
            f"Удалить датасет '{self.current_dataset}' и все его версии?",
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

            self.dataset_label.setText("Датасет: нет")
            self.version_label.setText("Версия: нет")
            self.data_table.table.setRowCount(0)
            self.distribution_plot.figure.clear()
            self.distribution_plot.canvas.draw()
            self.version_tree.tree.clear()

            QMessageBox.information(
                self,
                "Успех",
                f"Датасет '{dataset_name}' успешно удалён!"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось удалить датасет: {str(e)}"
            )
