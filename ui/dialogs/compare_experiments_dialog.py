# ui/dialogs/compare_experiments_dialog.py

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush


class CompareExperimentsSelectionDialog(QDialog):
    """
    Dialog to select two experiments for comparison.
    """
    
    def __init__(self, experiments: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор экспериментов для сравнения")
        self.setGeometry(100, 100, 600, 200)
        
        self.experiments = experiments
        self.exp1_id = None
        self.exp2_id = None
        
        # Create experiment entries list for display
        self.exp_entries = []
        for exp_id, data in experiments.items():
            dataset = data.get("dataset", {})
            model_type = data.get("model", {}).get("type", "N/A")
            timestamp = data.get("timestamp", "").split("T")[0]
            experiment_name = data.get("experiment_name")
            
            # Build display text with name if available
            if experiment_name:
                display_text = f"{exp_id} [{experiment_name}] - {dataset.get('name', 'N/A')} ({model_type}, {timestamp})"
            else:
                display_text = f"{exp_id} - {dataset.get('name', 'N/A')} ({model_type}, {timestamp})"
            
            self.exp_entries.append((exp_id, display_text))
        
        self._build_ui()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # First experiment selector
        layout.addWidget(QLabel("Первый эксперимент:"))
        self.combo1 = QComboBox()
        self.combo1.addItems([text for _, text in self.exp_entries])
        self.combo1.currentIndexChanged.connect(self._on_selection_changed)
        layout.addWidget(self.combo1)
        
        # Second experiment selector
        layout.addWidget(QLabel("Второй эксперимент:"))
        self.combo2 = QComboBox()
        self.combo2.addItems([text for _, text in self.exp_entries])
        if len(self.exp_entries) > 1:
            self.combo2.setCurrentIndex(1)
        self.combo2.currentIndexChanged.connect(self._on_selection_changed)
        layout.addWidget(self.combo2)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        ok_btn = QPushButton("Сравнить")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addStretch()
        layout.addLayout(button_layout)
    
    def _on_selection_changed(self):
        """Ensure different experiments are selected."""
        idx1 = self.combo1.currentIndex()
        idx2 = self.combo2.currentIndex()
        
        if idx1 == idx2 and len(self.exp_entries) > 1:
            # Auto-adjust second selection
            if idx2 == len(self.exp_entries) - 1:
                self.combo2.setCurrentIndex(idx2 - 1)
            else:
                self.combo2.setCurrentIndex(idx2 + 1)
    
    def get_selected_experiments(self):
        """Return the selected experiment IDs."""
        idx1 = self.combo1.currentIndex()
        idx2 = self.combo2.currentIndex()
        return (self.exp_entries[idx1][0], self.exp_entries[idx2][0])


class CompareExperimentsResultDialog(QDialog):
    """
    Dialog displaying comparison of two experiments side by side.
    """
    
    # Metrics where higher value is better
    HIGHER_IS_BETTER = {
        'accuracy', 'precision', 'recall', 'f1', 'f1_score', 'auc', 'roc_auc',
        'specificity', 'sensitivity', 'balanced_accuracy', 'avg_precision',
        'scores', 'mae' # Some contexts
    }
    
    # Metrics where lower value is better
    LOWER_IS_BETTER = {
        'loss', 'mse', 'rmse', 'mae', 'mean_absolute_error',
        'mean_squared_error', 'root_mean_squared_error', 'error',
        'cross_entropy', 'nll', 'bce', 'categorical_loss'
    }
    
    def __init__(self, exp1_data: dict, exp2_data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Сравнение экспериментов")
        self.setGeometry(50, 50, 1000, 700)
        
        self.exp1_data = exp1_data
        self.exp2_data = exp2_data
        
        self._build_ui()
    
    def _is_metric_better(self, metric_name: str, val1, val2):
        """
        Determine which metric value is better.
        Returns: 'val1', 'val2', or None (if equal)
        """
        if val1 is None or val2 is None:
            return None
        
        try:
            val1_float = float(val1)
            val2_float = float(val2)
        except (ValueError, TypeError):
            return None
        
        if val1_float == val2_float:
            return None
        
        metric_lower = metric_name.lower()
        
        # Check if higher is better
        for key in self.HIGHER_IS_BETTER:
            if key in metric_lower:
                return 'val1' if val1_float > val2_float else 'val2'
        
        # Check if lower is better
        for key in self.LOWER_IS_BETTER:
            if key in metric_lower:
                return 'val1' if val1_float < val2_float else 'val2'
        
        # Default: higher is better
        return 'val1' if val1_float > val2_float else 'val2'
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Сравнение экспериментов")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)
        
        # Create table
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Параметр", "Эксперимент 1", "Эксперимент 2"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Collect all data to display
        rows_data = []
        
        # Experiment IDs
        rows_data.append(["ID эксперимента", 
                         self.exp1_data.get("experiment_id", ""),
                         self.exp2_data.get("experiment_id", "")])
        
        # Experiment names
        exp1_name = self.exp1_data.get("experiment_name")
        exp2_name = self.exp2_data.get("experiment_name")
        if exp1_name or exp2_name:
            rows_data.append(["Название эксперимента", 
                             exp1_name or "—",
                             exp2_name or "—"])
        
        # Timestamps
        rows_data.append(["Время", 
                         self.exp1_data.get("timestamp", ""),
                         self.exp2_data.get("timestamp", "")])
        
        # Dataset info
        rows_data.append(["Датасет (название)", 
                         self.exp1_data.get("dataset", {}).get("name", ""),
                         self.exp2_data.get("dataset", {}).get("name", "")])
        
        rows_data.append(["Датасет (версия)", 
                         self.exp1_data.get("dataset", {}).get("version", ""),
                         self.exp2_data.get("dataset", {}).get("version", "")])
        
        # Target column
        rows_data.append(["Целевой столбец", 
                         self.exp1_data.get("target_column", ""),
                         self.exp2_data.get("target_column", "")])
        
        # Feature columns
        fc1 = self.exp1_data.get("feature_columns", [])
        fc2 = self.exp2_data.get("feature_columns", [])
        fc1_str = ", ".join(fc1) if fc1 else "—"
        fc2_str = ", ".join(fc2) if fc2 else "—"
        rows_data.append(["Столбцы признаков", fc1_str, fc2_str])
        
        # Model type
        rows_data.append(["Тип модели", 
                         self.exp1_data.get("model", {}).get("type", ""),
                         self.exp2_data.get("model", {}).get("type", "")])
        
        # Hyperparameters
        hp1 = self.exp1_data.get("model", {}).get("hyperparameters", {})
        hp2 = self.exp2_data.get("model", {}).get("hyperparameters", {})
        
        all_hp_keys = set(hp1.keys()) | set(hp2.keys())
        for key in sorted(all_hp_keys):
            rows_data.append([f"Параметр: {key}", 
                             str(hp1.get(key, "N/A")),
                             str(hp2.get(key, "N/A"))])
        
        # Metrics
        rows_data.append(["", "", ""])  # Separator
        metrics1 = self.exp1_data.get("metrics", {})
        metrics2 = self.exp2_data.get("metrics", {})
        
        all_metric_keys = set(metrics1.keys()) | set(metrics2.keys())
        metric_rows = []  # Store metric rows for special formatting
        for key in sorted(all_metric_keys):
            val1 = metrics1.get(key)
            val2 = metrics2.get(key)
            
            # Format float values
            if isinstance(val1, float):
                val1_str = f"{val1:.4f}"
            else:
                val1_str = str(val1) if val1 is not None else "N/A"
            
            if isinstance(val2, float):
                val2_str = f"{val2:.4f}"
            else:
                val2_str = str(val2) if val2 is not None else "N/A"
            
            metric_rows.append((f"Метрика: {key}", val1_str, val2_str, val1, val2, key))
            rows_data.append([f"Метрика: {key}", val1_str, val2_str])
        
        # Populate table
        table.setRowCount(len(rows_data))
        metrics_start_row = len(rows_data) - len(metric_rows)
        
        for row, (param, val1, val2) in enumerate(rows_data):
            # Parameter column
            item_param = QTableWidgetItem(param)
            item_param.setFlags(item_param.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 0, item_param)
            
            # Value 1 column
            item_val1 = QTableWidgetItem(val1)
            item_val1.setFlags(item_val1.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 1, item_val1)
            
            # Value 2 column
            item_val2 = QTableWidgetItem(val2)
            item_val2.setFlags(item_val2.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 2, item_val2)
            
            # Special formatting for metric rows
            if row >= metrics_start_row and row < len(rows_data):
                metric_row_idx = row - metrics_start_row
                if metric_row_idx < len(metric_rows):
                    _, _, _, raw_val1, raw_val2, metric_name = metric_rows[metric_row_idx]
                    better = self._is_metric_better(metric_name, raw_val1, raw_val2)
                    
                    if better == 'val1':
                        # Experiment 1 is better - green
                        item_val1.setBackground(QColor("#90ee90"))  # Light green
                        item_val1.setForeground(QColor("#1a1a1a"))  # Dark text
                        item_val2.setBackground(QColor("#ffcccc"))  # Light red
                        item_val2.setForeground(QColor("#1a1a1a"))  # Dark text
                    elif better == 'val2':
                        # Experiment 2 is better - green
                        item_val1.setBackground(QColor("#ffcccc"))  # Light red
                        item_val1.setForeground(QColor("#1a1a1a"))  # Dark text
                        item_val2.setBackground(QColor("#90ee90"))  # Light green
                        item_val2.setForeground(QColor("#1a1a1a"))  # Dark text
            # Highlight regular value differences (non-metric rows)
            elif val1 != val2 and val1 and val2 and param.strip():
                highlight_color = QColor("#e6f2ff")  # Light blue
                item_val1.setBackground(highlight_color)
                item_val1.setForeground(QColor("#1a1a1a"))  # Dark text for visibility
                item_val2.setBackground(highlight_color)
                item_val2.setForeground(QColor("#1a1a1a"))  # Dark text for visibility
        
        layout.addWidget(table)
        
        # Close button
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
