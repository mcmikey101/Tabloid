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
    QScrollArea
)
from PySide6.QtCore import Qt
from storage.file_store import FileStore
from experiments.registry import ExperimentManager
from core.dataset_manager import DatasetManager
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
        box = QGroupBox("Filters")
        layout = QFormLayout(box)

        self.dataset_filter = QComboBox()
        self.dataset_filter.addItem("All")

        self.model_filter = QComboBox()
        self.model_filter.addItem("All")

        layout.addRow("Dataset", self.dataset_filter)
        layout.addRow("Model", self.model_filter)

        return box

    # ---------------------------------------------------------
    # Experiments Table
    # ---------------------------------------------------------

    def _create_experiments_table(self):
        box = QGroupBox("Experiments")
        layout = QVBoxLayout(box)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Experiment ID",
            "Dataset",
            "Version",
            "Model",
            "Main Metric",
            "Date"
        ])

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.cellClicked.connect(self._on_row_selected)

        layout.addWidget(self.table)

        return box

    # ---------------------------------------------------------
    # Details Panel
    # ---------------------------------------------------------

    def _create_details_panel(self):
        box = QGroupBox("Experiment Details")
        layout = QVBoxLayout(box)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)

        # Button container
        buttons_layout = QHBoxLayout()
        
        self.export_model_button = QPushButton("Export Model")
        self.export_model_button.clicked.connect(self._on_export_model_clicked)
        buttons_layout.addWidget(self.export_model_button)
        
        self.delete_button = QPushButton("Delete Experiment")
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
            QMessageBox.warning(self, "Error", f"Failed to load experiments: {str(e)}")

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
        if dataset_name != "All":
            filters["dataset_name"] = dataset_name
        if model_type != "All":
            filters["model_type"] = model_type

        try:
            experiments = self.experiment_manager.list_experiments(**filters)
            self._display_experiments(experiments)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to refresh experiments: {str(e)}")
    
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
            
            # If there are any items, remove the "All" marker for comparison
            if "All" in current_items:
                current_items.discard("All")
            
            if available_datasets != current_items:
                # Rebuild the filter combo
                selected_index = self.dataset_filter.currentIndex()
                self.dataset_filter.clear()
                self.dataset_filter.addItem("All")
                self.dataset_filter.addItems(sorted(available_datasets))
                
                # Try to restore selection
                if current_filter and current_filter != "All":
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

            self.table.setItem(row, 0, QTableWidgetItem(exp_id))
            self.table.setItem(row, 1, QTableWidgetItem(dataset.get("name", "")))
            self.table.setItem(row, 2, QTableWidgetItem(dataset.get("version", "")))
            self.table.setItem(row, 3, QTableWidgetItem(data.get("model_type", "")))
            
            # Get the first metric from the metrics dictionary (works for all task types)
            # Classification: accuracy, Regression: mse, Clustering: silhouette_score
            main_metric = ""
            if metrics:
                first_metric_value = next(iter(metrics.values()))
                main_metric = str(first_metric_value) if first_metric_value is not None else ""
            self.table.setItem(row, 4, QTableWidgetItem(main_metric))
            
            # Format timestamp
            timestamp = data.get("timestamp", "")
            if timestamp:
                timestamp = timestamp.split("T")[0]  # Just date part
            self.table.setItem(row, 5, QTableWidgetItem(timestamp))

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
                QMessageBox.critical(self, "Error", f"Failed to load experiment: {str(e)}")

    def _show_experiment_details(self):
        """Display detailed information about selected experiment."""
        if not self.current_experiment_data:
            return

        lines = []
        data = self.current_experiment_data
        
        lines.append(f"Experiment ID: {data.get('experiment_id', '')}")
        lines.append(f"Timestamp: {data.get('timestamp', '')}")
        lines.append("")
        
        # Dataset info
        dataset = data.get("dataset", {})
        lines.append("=== Dataset ===")
        lines.append(f"Name: {dataset.get('name', '')}")
        lines.append(f"Version: {dataset.get('version', '')}")
        lines.append("")
        
        # Model info
        model = data.get("model", {})
        lines.append("=== Model ===")
        lines.append(f"Type: {model.get('type', '')}")
        lines.append("Hyperparameters:")
        for key, value in model.get("hyperparameters", {}).items():
            lines.append(f"  {key}: {value}")
        lines.append("")
        
        # Metrics
        lines.append("=== Metrics ===")
        for key, value in data.get("metrics", {}).items():
            if isinstance(value, float):
                lines.append(f"{key}: {value:.4f}")
            else:
                lines.append(f"{key}: {value}")
        
        # Notes
        if data.get("notes"):
            lines.append("")
            lines.append("=== Notes ===")
            lines.append(data.get("notes", ""))

        self.details_text.setText("\n".join(lines))

    # ---------------------------------------------------------
    # Export Model
    # ---------------------------------------------------------

    def _on_export_model_clicked(self):
        """Handle export model button click."""
        if not self.current_experiment_id:
            QMessageBox.warning(self, "Warning", "Please select an experiment first.")
            return

        try:
            # Check if model was saved
            try:
                model = self.experiment_manager.load_model(self.current_experiment_id)
            except FileNotFoundError:
                QMessageBox.warning(
                    self,
                    "Warning",
                    f"No saved model found for this experiment.\n"
                    f"Experiment ID: {self.current_experiment_id}"
                )
                return

            # Get experiment info for file naming
            model_type = self.current_experiment_data["model"]["type"]
            dataset_name = self.current_experiment_data["dataset"]["name"]
            
            # Show save dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Model",
                f"{dataset_name}_{model_type}_model",
                "Pickle files (*.pkl);;Joblib files (*.joblib)"
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
                    "Success",
                    f"Model exported successfully to:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Export Error",
                    f"Failed to export model:\n\n{str(e)}"
                )
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")
    
    def _on_delete_experiment_clicked(self):
        """Handle delete experiment button click."""
        if not self.current_experiment_id:
            QMessageBox.warning(self, "Warning", "Please select an experiment first.")
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete this experiment?\n\nExperiment ID: {self.current_experiment_id}",
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
                    "Success",
                    "Experiment deleted successfully!"
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
                    "Error",
                    "Failed to delete experiment."
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to delete experiment:\n\n{str(e)}"
            )
