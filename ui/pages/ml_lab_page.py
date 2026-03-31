# ui/pages/ml_lab_page.py

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QFormLayout,
    QSpinBox,
    QDoubleSpinBox,
    QTextEdit,
    QGroupBox,
    QMessageBox,
    QFileDialog,
    QInputDialog
)
from storage.file_store import FileStore
from core.dataset_manager import DatasetManager
from core.version_manager import VersionManager

from core import modeling
from core import evaluation

import pickle 
from pathlib import Path


class MLLabPage(QWidget):
    """
    1 Select dataset
    2 Select dataset version
    3 Select target column
    4 Select model
    5 Configure hyperparameters
    6 Train model
    7 Display metrics
    """

    def __init__(self):
        super().__init__()
        
        # Initialize managers
        self.file_store = FileStore()
        self.version_manager = VersionManager(file_store=self.file_store)
        self.dataset_manager = DatasetManager(
            version_manager=self.version_manager,
            file_store=self.file_store
        )
        
        self.current_df = None
        self.current_model = None
        self.current_splits = None
        
        self._build_ui()
        self._connect_signals()
        self._load_datasets()
        self._on_version_changed("raw")
        self._on_task_changed("Classification")

    # ---------------------------------------------------------
    # UI
    # ---------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(self._create_dataset_section())
        layout.addWidget(self._create_model_section())
        layout.addWidget(self._create_hyperparameter_section())
        layout.addWidget(self._create_training_section())
        layout.addWidget(self._create_metrics_section())

        layout.addStretch()

    # ---------------------------------------------------------
    # Dataset Selection
    # ---------------------------------------------------------
    def _create_dataset_section(self):
        box = QGroupBox("Dataset Selection")
        layout = QFormLayout(box)

        self.dataset_combo = QComboBox()
        self.version_combo = QComboBox()
        self.target_combo = QComboBox()

        layout.addRow("Dataset", self.dataset_combo)
        layout.addRow("Version", self.version_combo)
        layout.addRow("Target Column", self.target_combo)

        return box

    def _load_datasets(self):
        """Load available datasets into combo box."""
        datasets = self.dataset_manager.list_datasets()
        self.dataset_combo.addItems(datasets)

    def _on_dataset_changed(self, dataset_name):
        """Update versions when dataset changes."""
        if not dataset_name:
            return
        
        self.version_combo.clear()
        self.target_combo.clear()
        versions = self.dataset_manager.list_versions(dataset_name)
        self.version_combo.addItems(versions)

    def _on_version_changed(self, version_name):
        """Load dataframe and update target column options."""
        if not version_name:
            return
        
        dataset_name = self.dataset_combo.currentText()
        try:
            self.current_df = self.dataset_manager.load_version(
                dataset_name=dataset_name,
                version_name=version_name
            )
            self.target_combo.clear()
            self.target_combo.addItems(self.current_df.columns.tolist())
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load version: {str(e)}")

    # ---------------------------------------------------------
    # Model Selection
    # ---------------------------------------------------------
    def _create_model_section(self):
        box = QGroupBox("Model Selection")
        layout = QFormLayout(box)

        self.task_combo = QComboBox()
        self.task_combo.addItems([
            "Classification",
            "Regression",
            "Clustering"
        ])

        self.model_combo = QComboBox()

        layout.addRow("Task", self.task_combo)
        layout.addRow("Model", self.model_combo)

        return box

    def _on_task_changed(self, task):
        """Update model options based on selected task."""
        self.model_combo.clear()
        
        models = {
            "Classification": [
                "Logistic_Regression",
                "Random_Forest",
                "SVM",
                "XGBoost"
            ],
            "Regression": [
                "Linear_Regression",
                "RandomF_orest",
                "SVR",
                "XGBoost"
            ],
            "Clustering": [
                "KMeans",
                "GMM"
            ]
        }
        
        self.model_combo.addItems(models.get(task, []))

    def _on_model_changed(self, model): 
        """Show/hide hyperparameters based on selected model.""" 
        task = self.task_combo.currentText() 
        model_lower = model.lower()
        # Hide all by default
        self.n_estimators_label.hide()
        self.n_estimators.hide()
        self.n_clusters_label.hide()
        self.n_clusters.hide()
        self.n_components_label.hide()
        self.n_components.hide()
        self.covariance_type_label.hide()
        self.covariance_type.hide()
        self.n_init_label.hide()
        self.n_init.hide()

        # Show relevant parameters based on model
        if "forest" in model_lower or "xgboost" in model_lower:
            self.n_estimators_label.show()
            self.n_estimators.show()

        if model == "KMeans":
            self.n_clusters_label.show()
            self.n_clusters.show()

        if model == "GMM":
            self.n_components_label.show()
            self.n_components.show()
            self.covariance_type_label.show()
            self.covariance_type.show()
            self.n_init_label.show()
            self.n_init.show()

    # ---------------------------------------------------------
    # Hyperparameters
    # ---------------------------------------------------------
    def _create_hyperparameter_section(self):
        box = QGroupBox("Hyperparameters")
        layout = QFormLayout(box)

        self.test_size = QDoubleSpinBox()
        self.test_size.setRange(0.05, 0.5)
        self.test_size.setValue(0.2)
        self.test_size.setSingleStep(0.05)

        self.random_seed = QSpinBox()
        self.random_seed.setRange(0, 999999)
        self.random_seed.setValue(42)

        self.n_estimators = QSpinBox()
        self.n_estimators.setRange(10, 1000)
        self.n_estimators.setValue(100)
        self.n_estimators_label = QLabel("n_estimators")

        self.n_components = QSpinBox()
        self.n_components.setRange(1, 20)
        self.n_components.setValue(3)
        self.n_components_label = QLabel("Number of Components")

        self.covariance_type = QComboBox()
        self.covariance_type.addItems(["full", "tied", "diag", "spherical"])
        self.covariance_type_label = QLabel("Covariance Type")

        self.n_init = QSpinBox()
        self.n_init.setRange(1, 50)
        self.n_init.setValue(10)
        self.n_init_label = QLabel("n_init")

        self.n_clusters = QSpinBox()
        self.n_clusters.setRange(2, 20)
        self.n_clusters.setValue(3)
        self.n_clusters_label = QLabel("Number of Clusters")

        layout.addRow("Test Size", self.test_size)
        layout.addRow("Random Seed", self.random_seed)
        layout.addRow(self.n_estimators_label, self.n_estimators)
        layout.addRow(self.n_clusters_label, self.n_clusters)
        layout.addRow(self.n_components_label, self.n_components)
        layout.addRow(self.covariance_type_label, self.covariance_type)
        layout.addRow(self.n_init_label, self.n_init)

        return box

    # ---------------------------------------------------------
    # Training
    # ---------------------------------------------------------
    def _create_training_section(self):
        container = QWidget()
        layout = QHBoxLayout(container)

        self.train_button = QPushButton("Train Model")
        self.train_button.clicked.connect(self._on_train_clicked)

        self.export_button = QPushButton("Export Model")
        self.export_button.clicked.connect(self._on_export_clicked)
        self.export_button.setEnabled(False)

        layout.addStretch()
        layout.addWidget(self.train_button)
        layout.addWidget(self.export_button)

        return container

    def _on_train_clicked(self):
        """Train model with selected parameters."""
        if self.current_df is None:
            QMessageBox.warning(self, "Warning", "Please load a dataset version first.")
            return
        
        task = self.task_combo.currentText()
        model = self.model_combo.currentText()
        target_col = self.target_combo.currentText()

        if not target_col and task != "Clustering":
            QMessageBox.warning(self, "Warning", "Please select a target column.")
            return

        try:
            self.train_button.setEnabled(False)
            self.train_button.setText("Training...")
            
            if task == "Clustering":
                if model == "KMeans":
                    clustering_results = modeling.apply_clustering(
                        self.current_df,
                        method="kmeans",
                        random_seed=self.random_seed.value(),
                        n_clusters=self.n_clusters.value(),
                    )
                    labels = clustering_results["labels"]
                    self.current_model = clustering_results["model"]
                    self.current_df = clustering_results["result"]
                    metrics = {"silhouette_score": evaluation.evaluate_clustering(
                        self.current_df, labels
                    )}
                elif model == "GMM":
                    clustering_results = modeling.apply_clustering(
                        self.current_df,
                        method="gmm",
                        random_seed=self.random_seed.value(),
                        n_components=self.n_components.value(),
                        covariance_type=self.covariance_type.currentText(),
                        n_init=self.n_init.value()
                    )
                    labels = clustering_results["labels"]
                    self.current_model = clustering_results["model"]
                    self.current_df = clustering_results["result"]
                    metrics = {"silhouette_score": evaluation.evaluate_clustering(
                        self.current_df, labels
                    )}
                
                self.display_metrics(metrics)
                self.export_button.setEnabled(True)
                QMessageBox.information(self, "Success", "Clustering completed!")
                
                # Prompt to save as version
                save_version = QMessageBox.question(
                    self,
                    "Save as Version",
                    "Do you want to save this clustered dataset as a new version?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if save_version == QMessageBox.StandardButton.Yes:
                    self._save_clustering_as_version(labels, model)
            
            else:
                model_type = model.lower()
                task_type = task.lower()
                
                # Build model kwargs based on model type
                model_kwargs = {}
                if "forest" in model_type or "xgboost" in model_type:
                    model_kwargs["n_estimators"] = self.n_estimators.value()
                
                self.current_model, self.current_splits, config = modeling.train_model(
                    df=self.current_df,
                    target_column=target_col,
                    task_type=task_type,
                    model_type=model_type,
                    test_size=self.test_size.value(),
                    random_seed=self.random_seed.value(),
                    **model_kwargs
                )
                
                if task_type == "classification":
                    metrics = evaluation.evaluate_classification(
                        self.current_model,
                        self.current_splits["X_test"],
                        self.current_splits["y_test"]
                    )
                else:
                    metrics = evaluation.evaluate_regression(
                        self.current_model,
                        self.current_splits["X_test"],
                        self.current_splits["y_test"]
                    )
                
                self.display_metrics(metrics)
                self.export_button.setEnabled(True)
                QMessageBox.information(self, "Success", "Model training completed!")
            
        except Exception as e:
            QMessageBox.critical(self, "Training Error", f"Failed to train model: {str(e)}")
        finally:
            self.export_button.setEnabled(True)
            self.train_button.setEnabled(True)
            self.train_button.setText("Train Model")

    # ---------------------------------------------------------
    # Metrics
    # ---------------------------------------------------------
    def _create_metrics_section(self):
        box = QGroupBox("Model Metrics")
        layout = QVBoxLayout(box)

        self.metrics_text = QTextEdit()
        self.metrics_text.setReadOnly(True)

        layout.addWidget(self.metrics_text)

        return box

    def display_metrics(self, metrics: dict):
        """Display metrics in text area."""
        lines = []
        for key, value in metrics.items():
            if isinstance(value, float):
                lines.append(f"{key}: {value:.4f}")
            else:
                lines.append(f"{key}: {value}")

        self.metrics_text.setText("\n".join(lines))

    def _save_clustering_as_version(self, labels, model_name):
        """Save clustered dataset as a new version.""" 
        version_name, ok = QInputDialog.getText( self, "Save Version", "Enter new version name:" )
        if not ok or not version_name:
            return

        try:
            # Add cluster labels to dataframe
            result_df = self.current_df.copy()
            result_df["cluster"] = labels
            
            # Save as new version
            self.version_manager.create_version(
                dataset_name=self.dataset_combo.currentText(),
                version_name=version_name,
                df=result_df,
                parent_version=self.version_combo.currentText(),
                operation="clustering",
                config={
                    "model": model_name,
                    "n_clusters": self.n_clusters.value() if model_name == "KMeans" else self.n_components.value(),
                    "random_seed": self.random_seed.value()
                }
            )
            
            QMessageBox.information(
                self,
                "Success",
                f"Clustered version '{version_name}' saved successfully!"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save version: {str(e)}"
            )

    def _on_export_clicked(self): 
        """Export trained model to file.""" 
        if self.current_model is None: 
            QMessageBox.warning(self, "Warning", "No trained model to export.") 
            return
                
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Model",
            f"{self.dataset_combo.currentText()}_{self.task_combo.currentText()}_model",
            "Pickle files (*.pkl);;Joblib files (*.joblib)"
        )

        if not file_path:
            return

        try:
            if file_path.endswith('.pkl'):
                with open(file_path, 'wb') as f:
                    pickle.dump(self.current_model, f)
            else:  # joblib
                import joblib
                joblib.dump(self.current_model, file_path)
            
            QMessageBox.information(
                self,
                "Success",
                f"Model exported to {file_path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export model: {str(e)}"
            )

    # ---------------------------------------------------------
    # Signals
    # ---------------------------------------------------------
    def _connect_signals(self):
        """Connect UI signals."""
        self.dataset_combo.currentTextChanged.connect(self._on_dataset_changed)
        self.version_combo.currentTextChanged.connect(self._on_version_changed)
        self.task_combo.currentTextChanged.connect(self._on_task_changed)
        self.model_combo.currentTextChanged.connect(self._on_model_changed)