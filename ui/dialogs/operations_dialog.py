# ui/dialogs/operations_dialog.py

from typing import List, Dict, Tuple, Optional
import pandas as pd

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QComboBox,
    QCheckBox,
    QSpinBox,
    QDoubleSpinBox,
    QLabel,
    QWidget,
    QMessageBox,
    QInputDialog,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PySide6.QtCore import Qt

from core import preprocessing


class OperationsDialog(QDialog):
    """Dialog for building and applying data operations sequentially."""

    OPERATIONS = {
        "handle_missing_values": {
            "name": "Handle Missing Values",
            "requires_columns": False,
            "params": ["strategy"],
        },
        "drop_columns": {
            "name": "Drop Columns",
            "requires_columns": True,
            "params": [],
        },
        "drop_outliers": {
            "name": "Drop Outliers",
            "requires_columns": True,
            "params": ["method", "threshold"],
        },
        "drop_high_corr_features": {
            "name": "Drop High Corr Features",
            "requires_columns": False,
            "params": ["threshold"],
        },
        "standard_scale": {
            "name": "Standard Scale",
            "requires_columns": True,
            "params": [],
        },
        "minmax_scale": {
            "name": "Min-Max Scale",
            "requires_columns": True,
            "params": [],
        },
        "one_hot_encode": {
            "name": "One-Hot Encode",
            "requires_columns": True,
            "params": ["drop_first"],
        },
        "encode_classes": {
            "name": "Encode Classes",
            "requires_columns": True,
            "params": [],
        },
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Operations Builder")
        self.resize(900, 600)

        self.operations_sequence: List[Dict] = []
        self.result_df: Optional[pd.DataFrame] = None
        self.result_config: Optional[Dict] = None

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Top: operations list and add button
        top_layout = QHBoxLayout()

        ops_label = QLabel("Available Operations:")
        top_layout.addWidget(ops_label)
        top_layout.addStretch()

        self.operations_list = QListWidget()
        for op_id, op_info in self.OPERATIONS.items():
            self.operations_list.addItem(op_info["name"])

        top_layout_container = QWidget()
        top_layout_container.setLayout(top_layout)

        layout.addWidget(ops_label)
        layout.addWidget(self.operations_list)

        # Middle: selected operations sequence
        seq_label = QLabel("Operations Sequence:")
        layout.addWidget(seq_label)

        self.sequence_table = QTableWidget()
        self.sequence_table.setColumnCount(4)
        self.sequence_table.setHorizontalHeaderLabels(
            ["#", "Operation", "Configuration", "Actions"]
        )
        self.sequence_table.horizontalHeader().setStretchLastSection(False)
        self.sequence_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )

        layout.addWidget(self.sequence_table)

        # Buttons
        button_layout = QHBoxLayout()

        add_btn = QPushButton("Add Operation")
        add_btn.clicked.connect(self._add_operation)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_operation)

        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self._clear_operations)

        button_layout.addWidget(add_btn)
        button_layout.addWidget(remove_btn)
        button_layout.addWidget(clear_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        # Bottom: Apply and Save
        final_layout = QHBoxLayout()

        apply_preview_btn = QPushButton("Preview")
        apply_preview_btn.clicked.connect(self._preview_operations)

        save_btn = QPushButton("Apply & Save Version")
        save_btn.clicked.connect(self._save_version)

        final_layout.addStretch()
        final_layout.addWidget(apply_preview_btn)
        final_layout.addWidget(save_btn)

        layout.addLayout(final_layout)

    def set_dataframe(self, df: pd.DataFrame):
        """Set the input dataframe for operations."""
        self.input_df = df.copy()

    def _add_operation(self):
        """Add a new operation to the sequence."""
        current_row = self.operations_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select an operation.")
            return

        operation_names = list(self.OPERATIONS.keys())
        operation_id = operation_names[current_row]
        operation_info = self.OPERATIONS[operation_id]

        # Show configuration dialog
        config = self._configure_operation(operation_id)
        if config is None:
            return

        # Add to sequence
        self.operations_sequence.append({
            "operation": operation_id,
            "config": config,
        })

        self._update_sequence_table()

    def _configure_operation(self, operation_id: str) -> Optional[Dict]:
        """Show a configuration dialog for the selected operation."""
        operation_info = self.OPERATIONS[operation_id]
        config = {}

        # Handle column selection
        if operation_info["requires_columns"]:
            columns = self.input_df.columns.tolist()

            if operation_id == "encode_classes":
                # Single column selection
                col, ok = self._select_single_column(columns)
                if not ok:
                    return None
                config["column"] = col
            else:
                # Multiple columns selection
                cols = self._select_columns(columns)
                if cols is None:
                    return None
                config["columns"] = cols

        # Handle additional parameters
        if "strategy" in operation_info["params"]:
            strategies = ["mean", "median", "mode", "drop_rows", "drop_columns"]
            strategy, ok = self._select_from_list(
                strategies, "Select Missing Value Strategy:"
            )
            if not ok:
                return None
            config["strategy"] = strategy

        if "threshold" in operation_info["params"]:
            threshold, ok = self._get_float_input("Threshold:", 0.8)
            if not ok:
                return None
            config["threshold"] = threshold

        if "drop_first" in operation_info["params"]:
            drop_first = self._get_bool_input("Drop first category?")
            config["drop_first"] = drop_first

        if "method" in operation_info["params"]:
            methods = ["iqr", "z_score"]
            method, ok = self._select_from_list(
                methods, "Select Outlier Detection Method:"
            )
            if not ok:
                return None
            config["method"] = method 

        return config

    def _select_columns(self, columns: List[str]) -> Optional[List[str]]:
        """Show a dialog to select multiple columns."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Columns")
        dialog.resize(400, 300)

        layout = QVBoxLayout(dialog)

        label = QLabel("Select columns to apply operation:")
        layout.addWidget(label)

        list_widget = QListWidget()
        for col in columns:
            item = QListWidgetItem(col)
            item.setCheckState(Qt.CheckState.Unchecked)
            list_widget.addItem(item)

        layout.addWidget(list_widget)

        button_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")

        def on_ok():
            selected = [
                list_widget.item(i).text()
                for i in range(list_widget.count())
                if list_widget.item(i).checkState() == Qt.CheckState.Checked
            ]
            if not selected:
                QMessageBox.warning(dialog, "Warning", "Select at least one column.")
                return
            self.selected_columns = selected
            dialog.accept()

        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dialog.reject)

        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        if dialog.exec() == QDialog.Accepted:
            return self.selected_columns
        return None

    def _select_single_column(self, columns: List[str]) -> Tuple[str, bool]:
        """Show a dialog to select a single column."""
        col, ok = QInputDialog.getItem(
            self, "Select Column", "Choose a column:", columns, 0, False
        )
        return col, ok

    def _select_from_list(
        self, items: List[str], label: str
    ) -> Tuple[str, bool]:
        """Show a dialog to select from a list of items."""
        item, ok = QInputDialog.getItem(
            self, "Select Option", label, items, 0, False
        )
        return item, ok

    def _get_float_input(self, label: str, default: float = 0.5) -> Tuple[float, bool]:
        """Show a dialog to get a float input."""
        value, ok = QInputDialog.getDouble(
            self, "Input Value", label, default, 0.0, 1.0, 2
        )
        return value, ok

    def _get_bool_input(self, label: str) -> bool:
        """Show a dialog to get a boolean input."""
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Confirm")
        msg_box.setText(label)
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return msg_box.exec() == QMessageBox.StandardButton.Yes

    def _remove_operation(self):
        """Remove the selected operation from the sequence."""
        current_row = self.sequence_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Select an operation to remove.")
            return

        del self.operations_sequence[current_row]
        self._update_sequence_table()

    def _clear_operations(self):
        """Clear all operations."""
        reply = QMessageBox.question(
            self, "Confirm", "Clear all operations?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.operations_sequence = []
            self._update_sequence_table()

    def _update_sequence_table(self):
        """Update the operations sequence table."""
        self.sequence_table.setRowCount(len(self.operations_sequence))

        for idx, op in enumerate(self.operations_sequence):
            op_id = op["operation"]
            op_info = self.OPERATIONS[op_id]

            # Number
            num_item = QTableWidgetItem(str(idx + 1))
            num_item.setFlags(num_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.sequence_table.setItem(idx, 0, num_item)

            # Operation name
            name_item = QTableWidgetItem(op_info["name"])
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.sequence_table.setItem(idx, 1, name_item)

            # Configuration
            config_str = self._format_config(op["config"])
            config_item = QTableWidgetItem(config_str)
            config_item.setFlags(config_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.sequence_table.setItem(idx, 2, config_item)

            # Remove button
            remove_btn = QPushButton("Remove")
            remove_btn.clicked.connect(
                lambda checked, i=idx: self._remove_operation_at(i)
            )
            self.sequence_table.setCellWidget(idx, 3, remove_btn)

    def _remove_operation_at(self, idx: int):
        """Remove operation at specific index."""
        if 0 <= idx < len(self.operations_sequence):
            del self.operations_sequence[idx]
            self._update_sequence_table()

    def _format_config(self, config: Dict) -> str:
        """Format configuration dict as readable string."""
        parts = []
        for key, value in config.items():
            if isinstance(value, list):
                value_str = ", ".join(value[:3])
                if len(value) > 3:
                    value_str += "..."
            elif isinstance(value, dict):
                value_str = f"Dict({len(value)} items)"
            else:
                value_str = str(value)
            parts.append(f"{key}: {value_str}")
        return " | ".join(parts)

    def _preview_operations(self):
        """Preview the operations on the dataframe."""
        if not self.operations_sequence:
            QMessageBox.information(self, "Info", "No operations to preview.")
            return

        try:
            preview_df = self.input_df.copy()
            for op in self.operations_sequence:
                preview_df, _ = self._apply_operation(preview_df, op)

            msg = f"Preview Result:\n"
            msg += f"Shape: {preview_df.shape}\n"
            msg += f"Columns: {', '.join(preview_df.columns.tolist()[:5])}"
            if len(preview_df.columns) > 5:
                msg += f" ... ({len(preview_df.columns)} total)"

            QMessageBox.information(self, "Preview", msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error during preview: {str(e)}")

    def _apply_operations(self):
        """Apply all operations sequentially."""
        result_df = self.input_df.copy()
        operations_configs = []

        try:
            for op in self.operations_sequence:
                result_df, config = self._apply_operation(result_df, op)
                operations_configs.append(config)
        except Exception as e:
            raise Exception(f"Error during preprocessing: {str(e)}")

        self.result_df = result_df
        self.result_config = {
            "operations": operations_configs
        }

    def _apply_operation(
        self, df: pd.DataFrame, op: Dict
    ) -> Tuple[pd.DataFrame, Dict]:
        """Apply a single operation to the dataframe."""
        operation_id = op["operation"]
        config = op["config"]

        if operation_id == "handle_missing_values":
            return preprocessing.handle_missing_values(
                df,
                strategy=config.get("strategy", "mean"),
                columns=config.get("columns"),
            )
        elif operation_id == "drop_columns":
            return preprocessing.drop_columns(df, columns=config["columns"])
        elif operation_id == "drop_high_corr_features":
            return preprocessing.drop_high_corr_features(
                df, threshold=config.get("threshold", 0.8)
            )
        elif operation_id == "drop_outliers":
            return preprocessing.drop_outliers(
                df,
                columns=config.get("columns"),
                method=config.get("method", "iqr"),
                threshold=config.get("threshold", 1.5),
            )
        elif operation_id == "standard_scale":
            return preprocessing.standard_scale(df, columns=config["columns"])
        elif operation_id == "minmax_scale":
            return preprocessing.minmax_scale(df, columns=config["columns"])
        elif operation_id == "one_hot_encode":
            return preprocessing.one_hot_encode(
                df,
                columns=config["columns"],
                drop_first=config.get("drop_first", False),
            )
        elif operation_id == "encode_classes":
            return preprocessing.encode_classes(df, column=config["column"])
        else:
            raise ValueError(f"Unknown operation: {operation_id}")

    def _save_version(self):
        """Save the result as a new version."""
        if not self.operations_sequence:
            QMessageBox.warning(self, "Warning", "No operations to apply.")
            return

        try:
            self._apply_operations()

            if self.result_df is None:
                raise ValueError("Failed to apply operations.")

            QMessageBox.information(
                self,
                "Success",
                f"Operations applied successfully!\n"
                f"Result shape: {self.result_df.shape}\n"
                f"Result saved.",
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error applying operations: {str(e)}"
            )

    def get_results(self) -> Tuple[Optional[pd.DataFrame], Optional[Dict]]:
        """Get the resulting dataframe and operation config."""
        return self.result_df, self.result_config
