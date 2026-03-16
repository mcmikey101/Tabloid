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
    QGroupBox
)


class MLLabPage(QWidget):
    """
    ML Lab workflow:

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
        self._build_ui()

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
        self.model_combo.addItems([
            "LogisticRegression",
            "RandomForest",
            "XGBoost",
            "LinearRegression",
            "KMeans",
            "DBSCAN"
        ])

        layout.addRow("Task", self.task_combo)
        layout.addRow("Model", self.model_combo)

        return box

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

        layout.addRow("Test Size", self.test_size)
        layout.addRow("Random Seed", self.random_seed)
        layout.addRow("n_estimators", self.n_estimators)

        return box

    # ---------------------------------------------------------
    # Training
    # ---------------------------------------------------------

    def _create_training_section(self):
        container = QWidget()
        layout = QHBoxLayout(container)

        self.train_button = QPushButton("Train Model")

        layout.addStretch()
        layout.addWidget(self.train_button)

        return container

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

    # ---------------------------------------------------------
    # Utility
    # ---------------------------------------------------------

    def display_metrics(self, metrics: dict):
        lines = []

        for key, value in metrics.items():
            lines.append(f"{key}: {value}")

        self.metrics_text.setText("\n".join(lines))