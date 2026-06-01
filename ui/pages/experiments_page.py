# ui/pages/experiments_page.py

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QPushButton,
    QTextEdit,
    QGroupBox,
    QHeaderView,
    QMessageBox,
    QDialog,
    QInputDialog,
    QFileDialog,
    QScrollArea,
    QListWidget,
    QListWidgetItem,
    QSplitter,
)
from PySide6.QtCore import Qt


class NumericTableItem(QTableWidgetItem):
    """Custom table item for numeric sorting."""
    def __lt__(self, other):
        try:
            return float(self.text()) < float(other.text())
        except (ValueError, TypeError):
            return super().__lt__(other)
from storage.file_store import FileStore
from experiments.registry import ExperimentManager
from core.dataset_manager import DatasetManager
from ui.dialogs.compare_experiments_dialog import (
    CompareExperimentsSelectionDialog,
    CompareExperimentsResultDialog,
)
import pickle


class ExperimentsPage(QWidget):
    """
    Experiments browser.

    Shows previously run ML experiments with filtering
    and detailed inspection of a selected experiment.
    Users can apply saved models to dataset versions.
    """

    def __init__(self):
        super().__init__()
        
        # Initialize managers
        self.file_store = FileStore()
        self.experiment_manager = ExperimentManager()
        
        self.current_experiment_id = None
        self.current_experiment_data = None
        
        self._build_ui()
        self._load_initial_data()
    
    def showEvent(self, event):
        """Reload experiments data and refresh dataset filter when page is shown."""
        super().showEvent(event)
        self._reload_all_experiments()
        self._refresh_dataset_filter()

    # ---------------------------------------------------------
    # UI Construction
    # ---------------------------------------------------------

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create scroll area for responsive layout on small screens
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background-color: #262738; border: none; }")
        
        # Create content widget to hold all sections
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        layout.addWidget(self._create_filters())
        layout.addWidget(self._create_experiments_table())
        layout.addWidget(self._create_details_panel())
        
        scroll.setWidget(content)
        root_layout.addWidget(scroll)

    # ---------------------------------------------------------
    # Filters
    # ---------------------------------------------------------

    def _create_filters(self):
        box = QGroupBox("Фильтры")
        layout = QFormLayout(box)

        self.dataset_filter = QComboBox()
        self.dataset_filter.addItem("Все")

        self.model_filter = QComboBox()
        self.model_filter.addItem("Все")

        layout.addRow("Датасет", self.dataset_filter)
        layout.addRow("Модель", self.model_filter)

        return box

    # ---------------------------------------------------------
    # Experiments Table
    # ---------------------------------------------------------

    def _create_experiments_table(self):
        box = QGroupBox("Эксперименты")
        layout = QVBoxLayout(box)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID эксперимента",
            "Название",
            "Датасет",
            "Версия",
            "Модель",
            "Целевой столбец",
            "Главная метрика",
            "Дата"
        ])

        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.table.setSortingEnabled(True)
        self.table.cellClicked.connect(self._on_row_selected)

        layout.addWidget(self.table)

        return box

    # ---------------------------------------------------------
    # Details Panel
    # ---------------------------------------------------------

    def _create_details_panel(self):
        box = QGroupBox("Детали эксперимента")
        layout = QVBoxLayout(box)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)

        # Button container
        buttons_layout = QHBoxLayout()
        
        self.compare_button = QPushButton("Сравнить эксперименты")
        self.compare_button.clicked.connect(self._on_compare_clicked)
        buttons_layout.addWidget(self.compare_button)
        
        self.export_model_button = QPushButton("Экспорт модели")
        self.export_model_button.clicked.connect(self._on_export_model_clicked)
        buttons_layout.addWidget(self.export_model_button)
        
        self.delete_button = QPushButton("Удалить эксперимент")
        self.delete_button.clicked.connect(self._on_delete_experiment_clicked)
        buttons_layout.addWidget(self.delete_button)
        
        buttons_layout.addStretch()

        layout.addWidget(self.details_text)
        layout.addLayout(buttons_layout)

        return box

    # ---------------------------------------------------------
    # Data Loading
    # ---------------------------------------------------------

    def _load_initial_data(self):
        """Load initial data including experiments, datasets, and models."""
        try:
            # Load experiments
            experiments = self.experiment_manager.list_experiments()
            self._populate_filters(experiments)
            self._display_experiments(experiments)
            
            # Connect filter signals for auto-refresh
            self.dataset_filter.currentTextChanged.connect(self._on_filter_changed)
            self.model_filter.currentTextChanged.connect(self._on_filter_changed)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить эксперименты: {str(e)}")

    def _populate_filters(self, experiments: dict):
        """Populate filter dropdowns with unique values."""
        datasets = set()
        models = set()

        for exp_data in experiments.values():
            dataset = exp_data.get("dataset", {})
            if dataset.get("name"):
                datasets.add(dataset["name"])
            if exp_data.get("model_type"):
                models.add(exp_data["model_type"])

        # Update dataset filter
        for dataset in sorted(datasets):
            if self.dataset_filter.findText(dataset) == -1:
                self.dataset_filter.addItem(dataset)

        # Update model filter
        for model in sorted(models):
            if self.model_filter.findText(model) == -1:
                self.model_filter.addItem(model)

    def _on_filter_changed(self):
        """Handle filter changes and auto-refresh."""
        self._refresh_experiments()

    def _refresh_experiments(self):
        """Refresh experiments list with current filters."""
        dataset_name = self.dataset_filter.currentText()
        model_type = self.model_filter.currentText()

        filters = {}
        if dataset_name != "Все":
            filters["dataset_name"] = dataset_name
        if model_type != "Все":
            filters["model_type"] = model_type

        try:
            experiments = self.experiment_manager.list_experiments(**filters)
            self._display_experiments(experiments)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить эксперименты: {str(e)}")
    
    def _reload_all_experiments(self):
        """Reload all experiments and update filters."""
        try:
            experiments = self.experiment_manager.list_experiments()
            
            # Re-populate filters to catch any new datasets/models
            self._populate_filters(experiments)
            
            # Re-apply any active filters
            self._refresh_experiments()
        except Exception as e:
            # Silently ignore errors during reload
            pass
    
    def _refresh_dataset_filter(self):
        """Refresh dataset filter combo to include any new datasets."""
        try:
            # Get currently selected filter
            current_filter = self.dataset_filter.currentText()
            
            # Get all available datasets (including those without experiments)
            dataset_manager = DatasetManager()
            available_datasets = set(dataset_manager.list_datasets())
            
            # Check current items
            current_items = set(self.dataset_filter.itemText(i) for i in range(self.dataset_filter.count()))
            
            # If there are any items, remove the "Все" marker for comparison
            if "Все" in current_items:
                current_items.discard("Все")
            
            if available_datasets != current_items:
                # Rebuild the filter combo
                selected_index = self.dataset_filter.currentIndex()
                self.dataset_filter.clear()
                self.dataset_filter.addItem("Все")
                self.dataset_filter.addItems(sorted(available_datasets))
                
                # Try to restore selection
                if current_filter and current_filter != "Все":
                    index = self.dataset_filter.findText(current_filter)
                    if index >= 0:
                        self.dataset_filter.setCurrentIndex(index)
                    else:
                        self.dataset_filter.setCurrentIndex(0)
                else:
                    if selected_index < 0:
                        selected_index = 0
                    self.dataset_filter.setCurrentIndex(min(selected_index, self.dataset_filter.count() - 1))
        except Exception as e:
            # Silently ignore errors during refresh
            pass

    def _display_experiments(self, experiments: dict):
        """Display experiments in the table."""
        self.table.setRowCount(len(experiments))

        for row, (exp_id, data) in enumerate(experiments.items()):
            dataset = data.get("dataset", {})
            metrics = data.get("metrics", {})
            experiment_name = data.get("experiment_name")
            target_column = data.get("target_column", "")

            self.table.setItem(row, 0, QTableWidgetItem(exp_id))
            # Experiment name (show empty if not set)
            self.table.setItem(row, 1, QTableWidgetItem(experiment_name or ""))
            self.table.setItem(row, 2, QTableWidgetItem(dataset.get("name", "")))
            self.table.setItem(row, 3, QTableWidgetItem(dataset.get("version", "")))
            self.table.setItem(row, 4, QTableWidgetItem(data.get("model_type", "")))
            self.table.setItem(row, 5, QTableWidgetItem(target_column))
            
            # Get the first metric from the metrics dictionary (works for all task types)
            # Classification: accuracy, Regression: mse, Clustering: silhouette_score
            main_metric = ""
            if metrics:
                first_metric_value = next(iter(metrics.values()))
                main_metric = str(first_metric_value) if first_metric_value is not None else ""
            
            # Use NumericTableItem for proper numeric sorting
            metric_item = NumericTableItem(main_metric)
            self.table.setItem(row, 6, metric_item)
            
            # Format timestamp
            timestamp = data.get("timestamp", "")
            if timestamp:
                timestamp = timestamp.split("T")[0]  # Just date part
            self.table.setItem(row, 7, QTableWidgetItem(timestamp))

    # ---------------------------------------------------------
    # Selection & Details
    # ---------------------------------------------------------

    def _on_row_selected(self, row: int, column: int):
        """Handle row selection."""
        exp_id_item = self.table.item(row, 0)
        if exp_id_item:
            self.current_experiment_id = exp_id_item.text()
            try:
                self.current_experiment_data = self.experiment_manager.load_experiment(
                    self.current_experiment_id
                )
                self._show_experiment_details()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить эксперимент: {str(e)}")

    def _show_experiment_details(self):
        """Display detailed information about selected experiment."""
        if not self.current_experiment_data:
            return

        lines = []
        data = self.current_experiment_data
        
        lines.append(f"ID эксперимента: {data.get('experiment_id', '')}")
        
        # Experiment name
        experiment_name = data.get('experiment_name')
        if experiment_name:
            lines.append(f"Название: {experiment_name}")
        
        lines.append(f"Время: {data.get('timestamp', '')}")
        lines.append("")
        
        # Dataset info
        dataset = data.get("dataset", {})
        lines.append("=== Датасет ===")
        lines.append(f"Название: {dataset.get('name', '')}")
        lines.append(f"Версия: {dataset.get('version', '')}")
        lines.append("")
        
        # Target column and features
        target_column = data.get('target_column')
        feature_columns = data.get('feature_columns', [])
        lines.append("=== Столбцы ===")
        if target_column:
            lines.append(f"Целевой столбец: {target_column}")
        if feature_columns:
            lines.append(f"Столбцы-признаки ({len(feature_columns)}):")
            for col in feature_columns:
                lines.append(f"  • {col}")
        lines.append("")
        
        # Model info
        model = data.get("model", {})
        lines.append("=== Модель ===")
        lines.append(f"Тип: {model.get('type', '')}")
        lines.append("Гиперпараметры:")
        for key, value in model.get("hyperparameters", {}).items():
            lines.append(f"  {key}: {value}")
        lines.append("")
        
        # Metrics
        lines.append("=== Метрики ===")
        for key, value in data.get("metrics", {}).items():
            if isinstance(value, float):
                lines.append(f"{key}: {value:.4f}")
            else:
                lines.append(f"{key}: {value}")
        
        # Notes
        if data.get("notes"):
            lines.append("")
            lines.append("=== Заметки ===")
            lines.append(data.get("notes", ""))

        self.details_text.setText("\n".join(lines))

    # ---------------------------------------------------------
    # Export Model
    # ---------------------------------------------------------

    def _on_export_model_clicked(self):
        """Handle export model button click."""
        if not self.current_experiment_id:
            QMessageBox.warning(self, "Предупреждение", "Сначала выберите эксперимент.")
            return

        try:
            # Check if model was saved
            try:
                model = self.experiment_manager.load_model(self.current_experiment_id)
            except FileNotFoundError:
                QMessageBox.warning(
                    self,
                    "Предупреждение",
                    f"Для этого эксперимента нет сохранённой модели.\n"
                    f"ID эксперимента: {self.current_experiment_id}"
                )
                return

            # Get experiment info for file naming
            model_type = self.current_experiment_data["model"]["type"]
            dataset_name = self.current_experiment_data["dataset"]["name"]
            
            # Show save dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Экспорт модели",
                f"{dataset_name}_{model_type}_model",
                "Pickle-файлы (*.pkl);;Joblib-файлы (*.joblib)"
            )

            if not file_path:
                return

            # Save model
            try:
                if file_path.endswith('.pkl'):
                    with open(file_path, 'wb') as f:
                        pickle.dump(model, f)
                else:  # joblib
                    import joblib
                    joblib.dump(model, file_path)
                
                QMessageBox.information(
                    self,
                    "Успех",
                    f"Модель успешно экспортирована в:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Ошибка экспорта",
                    f"Не удалось экспортировать модель:\n\n{str(e)}"
                )
        
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта: {str(e)}")
    
    def _on_delete_experiment_clicked(self):
        """Handle delete experiment button click."""
        if not self.current_experiment_id:
            QMessageBox.warning(self, "Предупреждение", "Сначала выберите эксперимент.")
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Подтвердите удаление",
            f"Удалить этот эксперимент?\n\nID эксперимента: {self.current_experiment_id}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # Delete the experiment
            success = self.experiment_manager.delete_experiment(self.current_experiment_id)
            
            if success:
                QMessageBox.information(
                    self,
                    "Успех",
                    "Эксперимент успешно удалён!"
                )
                
                # Clear current experiment info
                self.current_experiment_id = None
                self.current_experiment_data = None
                self.details_text.clear()
                
                # Reload the experiments list
                self._reload_all_experiments()
            else:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Не удалось удалить эксперимент."
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось удалить эксперимент:\n\n{str(e)}"
            )

    # ---------------------------------------------------------
    # Compare Experiments
    # ---------------------------------------------------------

    def _on_compare_clicked(self):
        """Handle compare experiments button click."""
        try:
            # Get all experiments
            experiments = self.experiment_manager.list_experiments()
            
            if len(experiments) < 2:
                QMessageBox.warning(
                    self,
                    "Недостаточно данных",
                    "Требуется минимум 2 эксперимента для сравнения."
                )
                return
            
            # Open selection dialog
            dialog = CompareExperimentsSelectionDialog(experiments, self)
            if dialog.exec() == QDialog.Accepted:
                exp1_id, exp2_id = dialog.get_selected_experiments()
                
                # Load experiment data
                exp1_data = self.experiment_manager.load_experiment(exp1_id)
                exp2_data = self.experiment_manager.load_experiment(exp2_id)
                
                # Open comparison window
                compare_dialog = CompareExperimentsResultDialog(exp1_data, exp2_data, self)
                compare_dialog.exec()
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось выполнить сравнение:\n\n{str(e)}"
            )
