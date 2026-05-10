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
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QDialog,
    QScrollArea,
    QCheckBox,
    QProgressBar,
    QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from storage.file_store import FileStore
from core.dataset_manager import DatasetManager
from core.version_manager import VersionManager

from core import modeling
from core import evaluation
from experiments.registry import ExperimentManager
from ui.widgets.classification_plots import ConfusionMatrixWidget, ROCCurveWidget

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
        self.experiment_manager = ExperimentManager()
        
        self.current_df = None
        self.current_model = None
        self.current_splits = None
        self.current_y_test = None
        self.current_y_pred = None
        self.current_confusion_matrix = None
        self.current_roc_data = None
        
        self._build_ui()
        self._connect_signals()
        self._load_datasets()
        self._on_version_changed("raw")
        self._on_task_changed("Classification")

    def showEvent(self, event):
        """Refresh dataset list when page is shown."""
        super().showEvent(event)
        self._refresh_datasets()

    # ---------------------------------------------------------
    # UI
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

        layout.addWidget(self._create_dataset_section())
        layout.addWidget(self._create_model_section())
        layout.addWidget(self._create_hyperparameter_section())
        layout.addWidget(self._create_training_section())
        layout.addWidget(self._create_metrics_section())
        layout.addStretch()
        
        scroll.setWidget(content)
        root_layout.addWidget(scroll)

    # ---------------------------------------------------------
    # Dataset Selection
    # ---------------------------------------------------------
    def _create_dataset_section(self):
        box = QGroupBox("Dataset Selection")
        layout = QFormLayout(box)

        self.dataset_combo = QComboBox()
        self.version_combo = QComboBox()
        self.target_combo = QComboBox()
        
        self.feature_selection_btn = QPushButton("Select Features...")
        self.feature_selection_btn.clicked.connect(self._show_feature_selection_dialog)
        self.selected_features_label = QLabel("All features selected")

        layout.addRow("Dataset", self.dataset_combo)
        layout.addRow("Version", self.version_combo)
        layout.addRow("Target Column", self.target_combo)
        layout.addRow("Feature Columns", self.feature_selection_btn)
        layout.addRow("", self.selected_features_label)
        
        # Initialize selected features as None (means use all)
        self.selected_features = None

        return box
    
    def _show_feature_selection_dialog(self):
        """Show dialog to select feature columns."""
        if self.current_df is None:
            QMessageBox.warning(self, "Warning", "Please load a dataset version first.")
            return
        
        target_col = self.target_combo.currentText()
        available_cols = [col for col in self.current_df.columns if col != target_col]
        
        if not available_cols:
            QMessageBox.warning(self, "Warning", "No columns available for feature selection.")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Feature Columns")
        dialog.resize(400, 400)
        
        layout = QVBoxLayout(dialog)
        
        label = QLabel("Select columns to use as features:\n(Uncheck to exclude a column)")
        layout.addWidget(label)
        
        list_widget = QListWidget()
        for col in available_cols:
            item = QListWidgetItem(col)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            # Check if it was previously selected
            if self.selected_features is None or col in self.selected_features:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
            list_widget.addItem(item)
        
        layout.addWidget(list_widget)
        
        button_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        deselect_all_btn = QPushButton("Deselect All")
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        
        def select_all():
            for i in range(list_widget.count()):
                list_widget.item(i).setCheckState(Qt.CheckState.Checked)
        
        def deselect_all():
            for i in range(list_widget.count()):
                list_widget.item(i).setCheckState(Qt.CheckState.Unchecked)
        
        def on_ok():
            selected = []
            for i in range(list_widget.count()):
                if list_widget.item(i).checkState() == Qt.CheckState.Checked:
                    selected.append(list_widget.item(i).text())
            
            if not selected:
                QMessageBox.warning(dialog, "Warning", "Select at least one feature.")
                return
            
            self.selected_features = selected
            self._update_feature_chips_display()
            dialog.accept()
        
        select_all_btn.clicked.connect(select_all)
        deselect_all_btn.clicked.connect(deselect_all)
        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(deselect_all_btn)
        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        dialog.exec()
    
    def _update_feature_chips_display(self):
        """Update the feature chips display."""
        if self.selected_features is None:
            self.selected_features_label.setText("All features selected")
            self.selected_features_label.setStyleSheet("")
            return
        
        # Create a display string with feature names
        features_text = ", ".join(self.selected_features[:3])
        if len(self.selected_features) > 3:
            features_text += f"... (+{len(self.selected_features) - 3} more)"
        self.selected_features_label.setText(f"Features: {features_text}")
        self.selected_features_label.setStyleSheet("color: #51cf66; font-size: 9px;")

    def _load_datasets(self):
        """Load available datasets into combo box."""
        datasets = self.dataset_manager.list_datasets()
        self.dataset_combo.addItems(datasets)

    def _refresh_datasets(self):
        """Refresh the datasets list (called when page is shown)."""
        try:
            current_dataset = self.dataset_combo.currentText()
            datasets = self.dataset_manager.list_datasets()
            
            # Check if dataset list has changed
            current_items = [self.dataset_combo.itemText(i) for i in range(self.dataset_combo.count())]
            
            if set(current_items) != set(datasets):
                # Dataset list has changed, refresh it
                self.dataset_combo.clear()
                self.dataset_combo.addItems(datasets)
                
                # Try to restore previous selection, or select first item
                if current_dataset in datasets:
                    index = self.dataset_combo.findText(current_dataset)
                    self.dataset_combo.setCurrentIndex(index)
                else:
                    self.dataset_combo.setCurrentIndex(0)
        except Exception as e:
            print(f"Error refreshing datasets: {e}")

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
                "Random_Forest",
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
        
        # Hide all model-specific parameters by default
        self._hide_all_hyperparameters()
        
        # Show relevant parameters based on model
        if model == "Logistic_Regression":
            self._show_lr_hyperparameters()
        elif model == "Linear_Regression":
            pass  # Linear regression uses defaults
        elif "Random_Forest" in model:
            self._show_rf_hyperparameters()
        elif "SVM" in model or "SVR" in model:
            self._show_svm_hyperparameters()
        elif "XGBoost" in model:
            self._show_xgb_hyperparameters()
        elif model == "KMeans":
            self._show_kmeans_hyperparameters()
        elif model == "GMM":
            self._show_gmm_hyperparameters()
    
    def _hide_all_hyperparameters(self):
        """Hide all model-specific hyperparameter controls."""
        # Logistic Regression
        self.lr_c_label.hide()
        self.lr_c.hide()
        self.lr_max_iter_label.hide()
        self.lr_max_iter.hide()
        self.lr_solver_label.hide()
        self.lr_solver.hide()
        self.lr_penalty_label.hide()
        self.lr_penalty.hide()
        
        # Random Forest
        self.rf_n_estimators_label.hide()
        self.rf_n_estimators.hide()
        self.rf_max_depth_label.hide()
        self.rf_max_depth.hide()
        self.rf_min_samples_split_label.hide()
        self.rf_min_samples_split.hide()
        self.rf_min_samples_leaf_label.hide()
        self.rf_min_samples_leaf.hide()
        
        # SVM
        self.svm_c_label.hide()
        self.svm_c.hide()
        self.svm_kernel_label.hide()
        self.svm_kernel.hide()
        self.svm_gamma_label.hide()
        self.svm_gamma.hide()
        
        # XGBoost
        self.xgb_n_estimators_label.hide()
        self.xgb_n_estimators.hide()
        self.xgb_max_depth_label.hide()
        self.xgb_max_depth.hide()
        self.xgb_learning_rate_label.hide()
        self.xgb_learning_rate.hide()
        self.xgb_subsample_label.hide()
        self.xgb_subsample.hide()
        self.xgb_colsample_bytree_label.hide()
        self.xgb_colsample_bytree.hide()
        
        # KMeans
        self.kmeans_n_clusters_label.hide()
        self.kmeans_n_clusters.hide()
        self.kmeans_init_label.hide()
        self.kmeans_init.hide()
        self.kmeans_max_iter_label.hide()
        self.kmeans_max_iter.hide()
        
        # GMM
        self.gmm_n_components_label.hide()
        self.gmm_n_components.hide()
        self.gmm_covariance_type_label.hide()
        self.gmm_covariance_type.hide()
        self.gmm_n_init_label.hide()
        self.gmm_n_init.hide()
    
    def _show_lr_hyperparameters(self):
        """Show Logistic Regression hyperparameters."""
        self.lr_c_label.show()
        self.lr_c.show()
        self.lr_max_iter_label.show()
        self.lr_max_iter.show()
        self.lr_solver_label.show()
        self.lr_solver.show()
        self.lr_penalty_label.show()
        self.lr_penalty.show()
    
    def _show_rf_hyperparameters(self):
        """Show Random Forest hyperparameters."""
        self.rf_n_estimators_label.show()
        self.rf_n_estimators.show()
        self.rf_max_depth_label.show()
        self.rf_max_depth.show()
        self.rf_min_samples_split_label.show()
        self.rf_min_samples_split.show()
        self.rf_min_samples_leaf_label.show()
        self.rf_min_samples_leaf.show()
    
    def _show_svm_hyperparameters(self):
        """Show SVM/SVR hyperparameters."""
        self.svm_c_label.show()
        self.svm_c.show()
        self.svm_kernel_label.show()
        self.svm_kernel.show()
        self.svm_gamma_label.show()
        self.svm_gamma.show()
    
    def _show_xgb_hyperparameters(self):
        """Show XGBoost hyperparameters."""
        self.xgb_n_estimators_label.show()
        self.xgb_n_estimators.show()
        self.xgb_max_depth_label.show()
        self.xgb_max_depth.show()
        self.xgb_learning_rate_label.show()
        self.xgb_learning_rate.show()
        self.xgb_subsample_label.show()
        self.xgb_subsample.show()
        self.xgb_colsample_bytree_label.show()
        self.xgb_colsample_bytree.show()
    
    def _show_kmeans_hyperparameters(self):
        """Show KMeans hyperparameters."""
        self.kmeans_n_clusters_label.show()
        self.kmeans_n_clusters.show()
        self.kmeans_init_label.show()
        self.kmeans_init.show()
        self.kmeans_max_iter_label.show()
        self.kmeans_max_iter.show()
    
    def _show_gmm_hyperparameters(self):
        """Show GMM hyperparameters."""
        self.gmm_n_components_label.show()
        self.gmm_n_components.show()
        self.gmm_covariance_type_label.show()
        self.gmm_covariance_type.show()
        self.gmm_n_init_label.show()
        self.gmm_n_init.show()

    # ---------------------------------------------------------
    # Hyperparameters
    # ---------------------------------------------------------
    def _create_hyperparameter_section(self):
        box = QGroupBox("Configuration")
        layout = QVBoxLayout(box)

        # ===== Split Configuration (Global Parameters) =====
        split_group = QGroupBox("Split Configuration")
        split_layout = QFormLayout(split_group)
        
        self.test_size = QDoubleSpinBox()
        self.test_size.setRange(0.05, 0.5)
        self.test_size.setValue(0.2)
        self.test_size.setSingleStep(0.05)

        self.random_seed = QSpinBox()
        self.random_seed.setRange(0, 999999)
        self.random_seed.setValue(42)
        
        # Cross-validation
        self.use_cv = QCheckBox("Use K-Fold Cross-Validation")
        self.use_cv.setChecked(False)
        
        self.cv_folds = QSpinBox()
        self.cv_folds.setRange(2, 10)
        self.cv_folds.setValue(5)
        self.cv_folds.setEnabled(False)
        self.use_cv.toggled.connect(self.cv_folds.setEnabled)

        split_layout.addRow("Test Size", self.test_size)
        split_layout.addRow("Random Seed", self.random_seed)
        split_layout.addRow(self.use_cv)
        split_layout.addRow("K-Folds", self.cv_folds)
        
        layout.addWidget(split_group)
        
        # ===== Model Hyperparameters =====
        hp_group = QGroupBox("Model Hyperparameters")
        hp_layout = QFormLayout(hp_group)
        
        form_layout = hp_layout
        
        # ===== Logistic Regression =====
        self.lr_c = QDoubleSpinBox()
        self.lr_c.setRange(0.001, 100.0)
        self.lr_c.setValue(1.0)
        self.lr_c.setSingleStep(0.1)
        self.lr_c_label = QLabel("Logistic Regression - C")
        
        self.lr_max_iter = QSpinBox()
        self.lr_max_iter.setRange(1, 10000)
        self.lr_max_iter.setValue(100)
        self.lr_max_iter_label = QLabel("Max Iterations")
        
        self.lr_solver = QComboBox()
        self.lr_solver.addItems(["lbfgs", "liblinear", "newton-cholesky", "newton-cg", "sag", "saga"])
        self.lr_solver_label = QLabel("Solver")
        
        self.lr_penalty = QComboBox()
        self.lr_penalty.addItems(["l2", "l1", "elasticnet", "none"])
        self.lr_penalty_label = QLabel("Penalty")

        # ===== Random Forest =====
        self.rf_n_estimators = QSpinBox()
        self.rf_n_estimators.setRange(10, 1000)
        self.rf_n_estimators.setValue(100)
        self.rf_n_estimators_label = QLabel("Random Forest - n_estimators")
        
        self.rf_max_depth = QSpinBox()
        self.rf_max_depth.setRange(1, 100)
        self.rf_max_depth.setValue(10)
        self.rf_max_depth_label = QLabel("Max Depth")
        
        self.rf_min_samples_split = QSpinBox()
        self.rf_min_samples_split.setRange(2, 100)
        self.rf_min_samples_split.setValue(2)
        self.rf_min_samples_split_label = QLabel("Min Samples Split")
        
        self.rf_min_samples_leaf = QSpinBox()
        self.rf_min_samples_leaf.setRange(1, 100)
        self.rf_min_samples_leaf.setValue(1)
        self.rf_min_samples_leaf_label = QLabel("Min Samples Leaf")

        # ===== SVM / SVR =====
        self.svm_c = QDoubleSpinBox()
        self.svm_c.setRange(0.1, 1000.0)
        self.svm_c.setValue(1.0)
        self.svm_c.setSingleStep(0.1)
        self.svm_c_label = QLabel("SVM - C")
        
        self.svm_kernel = QComboBox()
        self.svm_kernel.addItems(["rbf", "linear", "poly", "sigmoid"])
        self.svm_kernel_label = QLabel("Kernel")
        
        self.svm_gamma = QComboBox()
        self.svm_gamma.addItems(["scale", "auto"])
        self.svm_gamma_label = QLabel("Gamma")

        # ===== XGBoost =====
        self.xgb_n_estimators = QSpinBox()
        self.xgb_n_estimators.setRange(10, 1000)
        self.xgb_n_estimators.setValue(100)
        self.xgb_n_estimators_label = QLabel("XGBoost - n_estimators")
        
        self.xgb_max_depth = QSpinBox()
        self.xgb_max_depth.setRange(1, 20)
        self.xgb_max_depth.setValue(6)
        self.xgb_max_depth_label = QLabel("Max Depth")
        
        self.xgb_learning_rate = QDoubleSpinBox()
        self.xgb_learning_rate.setRange(0.001, 1.0)
        self.xgb_learning_rate.setValue(0.1)
        self.xgb_learning_rate.setSingleStep(0.01)
        self.xgb_learning_rate_label = QLabel("Learning Rate")
        
        self.xgb_subsample = QDoubleSpinBox()
        self.xgb_subsample.setRange(0.1, 1.0)
        self.xgb_subsample.setValue(1.0)
        self.xgb_subsample.setSingleStep(0.1)
        self.xgb_subsample_label = QLabel("Subsample")
        
        self.xgb_colsample_bytree = QDoubleSpinBox()
        self.xgb_colsample_bytree.setRange(0.1, 1.0)
        self.xgb_colsample_bytree.setValue(1.0)
        self.xgb_colsample_bytree.setSingleStep(0.1)
        self.xgb_colsample_bytree_label = QLabel("Colsample by Tree")

        # ===== KMeans =====
        self.kmeans_n_clusters = QSpinBox()
        self.kmeans_n_clusters.setRange(2, 20)
        self.kmeans_n_clusters.setValue(3)
        self.kmeans_n_clusters_label = QLabel("KMeans - n_clusters")
        
        self.kmeans_init = QComboBox()
        self.kmeans_init.addItems(["k-means++", "random"])
        self.kmeans_init_label = QLabel("Init Method")
        
        self.kmeans_max_iter = QSpinBox()
        self.kmeans_max_iter.setRange(1, 1000)
        self.kmeans_max_iter.setValue(300)
        self.kmeans_max_iter_label = QLabel("Max Iterations")

        # ===== GMM =====
        self.gmm_n_components = QSpinBox()
        self.gmm_n_components.setRange(1, 20)
        self.gmm_n_components.setValue(3)
        self.gmm_n_components_label = QLabel("GMM - n_components")
        
        self.gmm_covariance_type = QComboBox()
        self.gmm_covariance_type.addItems(["full", "tied", "diag", "spherical"])
        self.gmm_covariance_type_label = QLabel("Covariance Type")
        
        self.gmm_n_init = QSpinBox()
        self.gmm_n_init.setRange(1, 50)
        self.gmm_n_init.setValue(10)
        self.gmm_n_init_label = QLabel("n_init")

        # Add all to layout (they'll be shown/hidden based on model selection)
        form_layout.addRow(self.lr_c_label, self.lr_c)
        form_layout.addRow(self.lr_max_iter_label, self.lr_max_iter)
        form_layout.addRow(self.lr_solver_label, self.lr_solver)
        form_layout.addRow(self.lr_penalty_label, self.lr_penalty)
        
        form_layout.addRow(self.rf_n_estimators_label, self.rf_n_estimators)
        form_layout.addRow(self.rf_max_depth_label, self.rf_max_depth)
        form_layout.addRow(self.rf_min_samples_split_label, self.rf_min_samples_split)
        form_layout.addRow(self.rf_min_samples_leaf_label, self.rf_min_samples_leaf)
        
        form_layout.addRow(self.svm_c_label, self.svm_c)
        form_layout.addRow(self.svm_kernel_label, self.svm_kernel)
        form_layout.addRow(self.svm_gamma_label, self.svm_gamma)
        
        form_layout.addRow(self.xgb_n_estimators_label, self.xgb_n_estimators)
        form_layout.addRow(self.xgb_max_depth_label, self.xgb_max_depth)
        form_layout.addRow(self.xgb_learning_rate_label, self.xgb_learning_rate)
        form_layout.addRow(self.xgb_subsample_label, self.xgb_subsample)
        form_layout.addRow(self.xgb_colsample_bytree_label, self.xgb_colsample_bytree)
        
        form_layout.addRow(self.kmeans_n_clusters_label, self.kmeans_n_clusters)
        form_layout.addRow(self.kmeans_init_label, self.kmeans_init)
        form_layout.addRow(self.kmeans_max_iter_label, self.kmeans_max_iter)
        
        form_layout.addRow(self.gmm_n_components_label, self.gmm_n_components)
        form_layout.addRow(self.gmm_covariance_type_label, self.gmm_covariance_type)
        form_layout.addRow(self.gmm_n_init_label, self.gmm_n_init)
        
        layout.addWidget(hp_group)

        return box

    # ---------------------------------------------------------
    # Training
    # ---------------------------------------------------------
    def _create_training_section(self):
        container = QWidget()
        layout = QVBoxLayout(container)

        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(8)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #1a1a25;
                padding: 0px;
            }
            QProgressBar::chunk {
                background-color: #5b7cfa;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Train button
        button_layout = QHBoxLayout()
        self.train_button = QPushButton("Train Model")
        self.train_button.setMinimumHeight(36)
        self.train_button.setStyleSheet("""
            QPushButton {
                background-color: #5b7cfa;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4c63d2;
            }
        """)
        self.train_button.clicked.connect(self._on_train_clicked)

        self.export_button = QPushButton("Show on Experiments Page")
        self.export_button.setMinimumHeight(36)
        self.export_button.clicked.connect(self._on_show_experiments_clicked)
        self.export_button.setEnabled(False)

        button_layout.addStretch()
        button_layout.addWidget(self.train_button)
        button_layout.addWidget(self.export_button)
        
        layout.addLayout(button_layout)

        return container
    
    def _get_current_hyperparameters(self) -> dict:
        """Get current hyperparameter values from UI."""
        model_name = self.model_combo.currentText()
        hyperparams = {}
        
        if model_name == "Logistic_Regression":
            hyperparams["C"] = self.lr_c.value()
            hyperparams["max_iter"] = self.lr_max_iter.value()
            hyperparams["solver"] = self.lr_solver.currentText()
            hyperparams["penalty"] = self.lr_penalty.currentText()
        
        elif model_name == "Random_Forest":
            hyperparams["n_estimators"] = self.rf_n_estimators.value()
            hyperparams["max_depth"] = self.rf_max_depth.value()
            hyperparams["min_samples_split"] = self.rf_min_samples_split.value()
            hyperparams["min_samples_leaf"] = self.rf_min_samples_leaf.value()
        
        elif model_name == "SVM" or model_name == "SVR":
            hyperparams["C"] = self.svm_c.value()
            hyperparams["kernel"] = self.svm_kernel.currentText()
            hyperparams["gamma"] = self.svm_gamma.currentText()
        
        elif model_name == "XGBoost":
            hyperparams["n_estimators"] = self.xgb_n_estimators.value()
            hyperparams["max_depth"] = self.xgb_max_depth.value()
            hyperparams["learning_rate"] = self.xgb_learning_rate.value()
            hyperparams["subsample"] = self.xgb_subsample.value()
            hyperparams["colsample_bytree"] = self.xgb_colsample_bytree.value()
        
        elif model_name == "KMeans":
            hyperparams["n_clusters"] = self.kmeans_n_clusters.value()
            hyperparams["init"] = self.kmeans_init.currentText()
            hyperparams["max_iter"] = self.kmeans_max_iter.value()
        
        elif model_name == "GMM":
            hyperparams["n_components"] = self.gmm_n_components.value()
            hyperparams["covariance_type"] = self.gmm_covariance_type.currentText()
            hyperparams["n_init"] = self.gmm_n_init.value()
        
        hyperparams["test_size"] = self.test_size.value()
        
        return hyperparams
    
    def _run_training(self, training_params: dict) -> dict:
        """
        Run the actual training logic. This method runs in a worker thread.
        
        Args:
            training_params: Dictionary containing all parameters needed for training
            
        Returns:
            Dictionary with training results
        """
        df = training_params["df"]
        task = training_params["task"]
        model = training_params["model"]
        target_col = training_params["target_col"]
        
        # Prepare dataframe with selected features
        if self.selected_features is not None and task != "Clustering":
            # For supervised learning, use selected features + target
            cols_to_use = list(self.selected_features) + [target_col]
            df = df[cols_to_use]
        elif self.selected_features is not None and task == "Clustering":
            # For clustering, use only selected features
            df = df[self.selected_features]
        
        results = {}
        
        if task == "Clustering":
            if model == "KMeans":
                clustering_results = modeling.apply_clustering(
                    df,
                    method="kmeans",
                    random_seed=self.random_seed.value(),
                    n_clusters=self.kmeans_n_clusters.value(),
                    init=self.kmeans_init.currentText(),
                    max_iter=self.kmeans_max_iter.value(),
                )
                labels = clustering_results["labels"]
                results["model"] = clustering_results["model"]
                results["df"] = clustering_results["result"]
                results["labels"] = labels
                results["task"] = task
                results["model_name"] = model
                metrics = {"silhouette_score": evaluation.evaluate_clustering(
                    clustering_results["result"], labels
                )}
                results["metrics"] = metrics
            elif model == "GMM":
                clustering_results = modeling.apply_clustering(
                    df,
                    method="gmm",
                    random_seed=self.random_seed.value(),
                    n_components=self.gmm_n_components.value(),
                    covariance_type=self.gmm_covariance_type.currentText(),
                    n_init=self.gmm_n_init.value()
                )
                labels = clustering_results["labels"]
                results["model"] = clustering_results["model"]
                results["df"] = clustering_results["result"]
                results["labels"] = labels
                results["task"] = task
                results["model_name"] = model
                metrics = {"silhouette_score": evaluation.evaluate_clustering(
                    clustering_results["result"], labels
                )}
                results["metrics"] = metrics
        else:
            model_type = model.lower()
            task_type = task.lower()
            
            # Build model kwargs based on model type with all the new hyperparameters
            model_kwargs = {}
            
            if model == "Logistic_Regression":
                model_kwargs["C"] = self.lr_c.value()
                model_kwargs["max_iter"] = self.lr_max_iter.value()
                model_kwargs["solver"] = self.lr_solver.currentText()
                model_kwargs["penalty"] = self.lr_penalty.currentText()
            
            elif model == "Random_Forest":
                model_kwargs["n_estimators"] = self.rf_n_estimators.value()
                model_kwargs["max_depth"] = self.rf_max_depth.value()
                model_kwargs["min_samples_split"] = self.rf_min_samples_split.value()
                model_kwargs["min_samples_leaf"] = self.rf_min_samples_leaf.value()
            
            elif model == "SVM":
                model_kwargs["C"] = self.svm_c.value()
                model_kwargs["kernel"] = self.svm_kernel.currentText()
                model_kwargs["gamma"] = self.svm_gamma.currentText()
            
            elif model == "SVR":
                model_kwargs["C"] = self.svm_c.value()
                model_kwargs["kernel"] = self.svm_kernel.currentText()
                model_kwargs["gamma"] = self.svm_gamma.currentText()
            
            elif model == "XGBoost":
                model_kwargs["n_estimators"] = self.xgb_n_estimators.value()
                model_kwargs["max_depth"] = self.xgb_max_depth.value()
                model_kwargs["learning_rate"] = self.xgb_learning_rate.value()
                model_kwargs["subsample"] = self.xgb_subsample.value()
                model_kwargs["colsample_bytree"] = self.xgb_colsample_bytree.value()
            
            current_model, current_splits, config = modeling.train_model(
                df=df,
                target_column=target_col,
                task_type=task_type,
                model_type=model_type,
                test_size=self.test_size.value(),
                random_seed=self.random_seed.value(),
                **model_kwargs
            )
            
            if task_type == "classification":
                metrics = evaluation.evaluate_classification(
                    current_model,
                    current_splits["X_test"],
                    current_splits["y_test"]
                )
                
                # Get confusion matrix and ROC curve data for classification
                cm_data = evaluation.get_confusion_matrix(
                    current_model,
                    current_splits["X_test"],
                    current_splits["y_test"]
                )
                results["confusion_matrix_data"] = cm_data
                
                try:
                    roc_data = evaluation.get_roc_curve_data(
                        current_model,
                        current_splits["X_test"],
                        current_splits["y_test"]
                    )
                    results["roc_curve_data"] = roc_data
                except Exception as e:
                    print(f"Could not generate ROC curve: {e}")
                    results["roc_curve_data"] = None
            else:
                metrics = evaluation.evaluate_regression(
                    current_model,
                    current_splits["X_test"],
                    current_splits["y_test"]
                )
            
            results["model"] = current_model
            results["splits"] = current_splits
            results["config"] = config
            results["metrics"] = metrics
            results["task"] = task
            results["model_name"] = model
        
        return results

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
            # Disable training button during training
            self.train_button.setEnabled(False)
            
            # Run training synchronously
            result = self._run_training({
                "df": self.current_df.copy(),
                "task": task,
                "model": model,
                "target_col": target_col,
            })
            
            # Handle training completion
            self.train_button.setEnabled(True)
            
            # Update model state
            self.current_model = result["model"]
            if "df" in result:
                self.current_df = result["df"]
            if "splits" in result:
                self.current_splits = result["splits"]
            
            # Store confusion matrix and ROC curve data for classification
            if result["task"] == "Classification":
                if "confusion_matrix_data" in result:
                    self.current_confusion_matrix = result["confusion_matrix_data"]
                if "roc_curve_data" in result:
                    self.current_roc_data = result["roc_curve_data"]
            
            # Display metrics
            self.display_metrics(result["metrics"], result["task"])
            self.export_button.setEnabled(True)
            
            # Ask user if they want to save the experiment
            save_experiment = QMessageBox.question(
                self,
                "Save Experiment",
                "Do you want to save this experiment?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if save_experiment == QMessageBox.StandardButton.Yes:
                try:
                    dataset_name = self.dataset_combo.currentText()
                    version_name = self.version_combo.currentText()
                    model_name = result["model_name"]
                    task = result["task"]
                    
                    # Build hyperparameters dict from UI
                    hyperparams = self._get_current_hyperparameters()
                    
                    # Build description with training task
                    notes = f"Training task: {task}"
                    
                    # Save experiment with model
                    experiment_id = self.experiment_manager.create_experiment(
                        dataset_name=dataset_name,
                        dataset_version=version_name,
                        model_type=model_name,
                        hyperparameters=hyperparams,
                        metrics=result["metrics"],
                        random_seed=self.random_seed.value(),
                        model_object=self.current_model,
                        notes=notes
                    )
                    
                    # Show experiment saved notification
                    QMessageBox.information(
                        self,
                        "Experiment Saved",
                        f"Experiment successfully saved!\n"
                        f"Experiment ID: {experiment_id}"
                    )
                except Exception as e:
                    QMessageBox.warning(
                        self,
                        "Warning",
                        f"Model trained but failed to save experiment:\n{str(e)}\n\n"
                        f"You can still use the model in this session."
                    )
            
            # Determine success message
            if result["task"] == "Clustering":
                QMessageBox.information(self, "Success", "Clustering completed!")
                
                # Prompt to save as version for clustering
                save_version = QMessageBox.question(
                    self,
                    "Save as Version",
                    "Do you want to save this clustered dataset as a new version?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if save_version == QMessageBox.StandardButton.Yes:
                    self._save_clustering_as_version(result["labels"], result["model_name"])
            else:
                QMessageBox.information(self, "Success", "Model training completed!")
        
        except Exception as e:
            self.train_button.setEnabled(True)
            QMessageBox.critical(self, "Error", f"Error during training:\n\n{str(e)}")

    # ---------------------------------------------------------
    # Metrics
    # ---------------------------------------------------------
    def _create_metrics_section(self):
        box = QGroupBox("Model Metrics")
        layout = QVBoxLayout(box)

        # Metrics container
        self.metrics_container = QWidget()
        self.metrics_layout = QVBoxLayout(self.metrics_container)
        self.metrics_layout.setSpacing(12)
        self.metrics_layout.setContentsMargins(0, 0, 0, 0)
        
        # Empty state
        self.metrics_empty = QLabel("No model trained yet")
        self.metrics_empty.setStyleSheet("color: #999999; font-size: 10px;")
        self.metrics_layout.addWidget(self.metrics_empty)
        
        layout.addWidget(self.metrics_container)
        
        # Confusion matrix and ROC curve widgets (initially hidden)
        self.confusion_matrix_widget = ConfusionMatrixWidget()
        self.confusion_matrix_widget.setVisible(False)
        layout.addWidget(self.confusion_matrix_widget)
        
        self.roc_curve_widget = ROCCurveWidget()
        self.roc_curve_widget.setVisible(False)
        layout.addWidget(self.roc_curve_widget)
        
        layout.addStretch()

        return box

    def display_metrics(self, metrics: dict, task: str = None):
        """Display metrics as formatted cards with visual indicators."""
        # Clear previous metrics
        while self.metrics_layout.count():
            item = self.metrics_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not metrics:
            self.metrics_empty = QLabel("No metrics available")
            self.metrics_empty.setStyleSheet("color: #999999; font-size: 10px;")
            self.metrics_layout.addWidget(self.metrics_empty)
            return
        
        # Display each metric as a card
        first = True
        for key, value in metrics.items():
            metric_card = self._create_metric_card(key, value, is_main=first)
            self.metrics_layout.addWidget(metric_card)
            first = False
        
        self.metrics_layout.addStretch()
        
        # Display confusion matrix and ROC curve for classification
        if task == "Classification":
            self.confusion_matrix_widget.setVisible(False)
            self.roc_curve_widget.setVisible(False)
            
            if self.current_confusion_matrix is not None:
                self.confusion_matrix_widget.set_data(
                    self.current_confusion_matrix["confusion_matrix"],
                    self.current_confusion_matrix["classes"],
                    self.current_confusion_matrix["y_test"],
                    self.current_confusion_matrix["y_pred"]
                )
                self.confusion_matrix_widget.setVisible(True)
            
            if self.current_roc_data is not None and self.current_roc_data:
                self.roc_curve_widget.set_data(self.current_roc_data)
                self.roc_curve_widget.setVisible(True)
    
    def _create_metric_card(self, name: str, value, is_main: bool = False) -> QFrame:
        """Create a styled metric card with visual indicators."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1a1a25;
                border: 1px solid #3a3d4a;
                border-radius: 4px;
                padding: 12px;
            }
        """)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # Metric name
        name_label = QLabel(f"{name}:" if not is_main else "Main Metric:")
        name_label.setStyleSheet("color: #b0b0b0; font-weight: bold;" if not is_main else "color: #e0e0e0; font-weight: bold; font-size: 11px;")
        layout.addWidget(name_label)
        
        # Format value
        if isinstance(value, float):
            value_str = f"{value:.4f}"
        else:
            value_str = str(value)
        
        # Metric value with color indicator (for classification metrics)
        value_label = QLabel(value_str)
        value_font = QFont()
        value_font.setBold(True)
        value_font.setPointSize(11 if is_main else 10)
        value_label.setFont(value_font)
        
        # Color code based on accuracy/score thresholds (for metrics like accuracy, f1, etc.)
        if isinstance(value, (int, float)) and 0 <= value <= 1:
            if value >= 0.85:
                color = "#51cf66"  # Green
            elif value >= 0.70:
                color = "#ffd43b"  # Yellow
            else:
                color = "#ff6b6b"  # Red
            value_label.setStyleSheet(f"color: {color};")
        else:
            value_label.setStyleSheet("color: #51cf66;")
        
        layout.addWidget(value_label)
        layout.addStretch()
        
        return card

    def _save_clustering_as_version(self, labels, model_name):
        """Save clustered dataset as a new version.""" 
        version_name, ok = QInputDialog.getText( self, "Save Version", "Enter new version name:" )
        if not ok or not version_name:
            return

        try:
            # Add cluster labels to dataframe
            result_df = self.current_df.copy()
            result_df["cluster"] = labels
            
            # Determine cluster count based on model
            if model_name == "KMeans":
                n_clusters = self.kmeans_n_clusters.value()
            else:  # GMM
                n_clusters = self.gmm_n_components.value()
            
            # Save as new version
            self.version_manager.create_version(
                dataset_name=self.dataset_combo.currentText(),
                version_name=version_name,
                df=result_df,
                parent_version=self.version_combo.currentText(),
                operation="clustering",
                config={
                    "model": model_name,
                    "n_clusters": n_clusters,
                    "random_seed": self.random_seed.value()
                }
            )
            
            # Refresh version combo to show the new version
            dataset_name = self.dataset_combo.currentText()
            self.version_combo.clear()
            versions = self.dataset_manager.list_versions(dataset_name)
            self.version_combo.addItems(versions)
            
            # Set the new version as current and explicitly refresh display
            index = self.version_combo.findText(version_name)
            if index >= 0:
                self.version_combo.setCurrentIndex(index)
                # Explicitly call version changed handler to ensure UI updates immediately
                self._on_version_changed(version_name)
            
            # Update version tree on datasets page
            self._update_datasets_page_version_tree(dataset_name)
            
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

    def _on_show_experiments_clicked(self):
        """Navigate to the experiments page."""
        # Get the main window
        main_window = self.window()
        
        # Navigate to experiments page (index 1 in QStackedWidget)
        if hasattr(main_window, 'pages'):
            main_window.pages.setCurrentIndex(1)
    
    def _update_datasets_page_version_tree(self, dataset_name: str):
        """Update version tree on datasets page after new version is created."""
        try:
            main_window = self.window()
            if hasattr(main_window, 'pages'):
                # Get the datasets page (index 0 in QStackedWidget)
                datasets_page = main_window.pages.widget(0)
                if datasets_page and hasattr(datasets_page, 'load_dataset'):
                    # Reload the dataset to show new version in tree
                    datasets_page.load_dataset(dataset_name)
        except Exception as e:
            # Silently fail if we can't update the datasets page
            pass

    # ---------------------------------------------------------
    # Signals
    # ---------------------------------------------------------
    def _connect_signals(self):
        """Connect UI signals."""
        self.dataset_combo.currentTextChanged.connect(self._on_dataset_changed)
        self.version_combo.currentTextChanged.connect(self._on_version_changed)
        self.task_combo.currentTextChanged.connect(self._on_task_changed)
        self.model_combo.currentTextChanged.connect(self._on_model_changed)