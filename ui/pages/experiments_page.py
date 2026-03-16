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
    QHeaderView
)


class ExperimentsPage(QWidget):
    """
    Experiments browser.

    Shows previously run ML experiments with filtering
    and detailed inspection of a selected experiment.
    """

    def __init__(self):
        super().__init__()
        self._build_ui()

    # ---------------------------------------------------------
    # UI Construction
    # ---------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(self._create_filters())
        layout.addWidget(self._create_experiments_table())
        layout.addWidget(self._create_details_panel())

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

        self.refresh_button = QPushButton("Refresh")

        layout.addRow("Dataset", self.dataset_filter)
        layout.addRow("Model", self.model_filter)
        layout.addRow("", self.refresh_button)

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
            "Accuracy",
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

        self.load_model_button = QPushButton("Load Model")

        layout.addWidget(self.details_text)
        layout.addWidget(self.load_model_button)

        return box

    # ---------------------------------------------------------
    # Table Data
    # ---------------------------------------------------------

    def load_experiments(self, experiments: dict):
        """
        experiments format example:

        {
            "exp_id": {
                "timestamp": "...",
                "dataset": {"name": "...", "version": "..."},
                "model_type": "...",
                "metrics": {"accuracy": 0.95}
            }
        }
        """

        self.table.setRowCount(len(experiments))

        for row, (exp_id, data) in enumerate(experiments.items()):
            dataset = data.get("dataset", {})
            metrics = data.get("metrics", {})

            self.table.setItem(row, 0, QTableWidgetItem(exp_id))
            self.table.setItem(row, 1, QTableWidgetItem(dataset.get("name", "")))
            self.table.setItem(row, 2, QTableWidgetItem(dataset.get("version", "")))
            self.table.setItem(row, 3, QTableWidgetItem(data.get("model_type", "")))
            self.table.setItem(row, 4, QTableWidgetItem(str(metrics.get("accuracy", ""))))
            self.table.setItem(row, 5, QTableWidgetItem(data.get("timestamp", "")))

    # ---------------------------------------------------------
    # Selection
    # ---------------------------------------------------------

    def _on_row_selected(self, row, column):
        exp_id_item = self.table.item(row, 0)
        if exp_id_item:
            exp_id = exp_id_item.text()
            self.show_experiment_details({"experiment_id": exp_id})

    # ---------------------------------------------------------
    # Details Display
    # ---------------------------------------------------------

    def show_experiment_details(self, details: dict):
        lines = []
        for key, value in details.items():
            lines.append(f"{key}: {value}")

        self.details_text.setText("\n".join(lines))