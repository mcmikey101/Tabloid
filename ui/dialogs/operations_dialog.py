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
    QApplication,
    QAbstractItemView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from core import preprocessing
from ui.widgets.column_selector import ColumnSelectorPanel


# Operation groups and metadata
OPERATION_GROUPS = {
    "Cleaning": [
        ("handle_missing_values", "Handle Missing Values", "Fill or remove rows with missing data using mean, median, mode, or drop strategies"),
        ("drop_columns", "Drop Columns", "Remove specified columns from the dataset"),
        ("drop_outliers", "Drop Outliers", "Remove rows with outlier values using IQR or Z-score methods"),
        ("drop_high_corr_features", "Drop High Corr Features", "Remove highly correlated features (default: >0.95 correlation). Uses Pearson correlation coefficient."),
    ],
    "Scaling": [
        ("standard_scale", "Standard Scale", "Normalize features to mean=0, std=1 using z-score normalization (x = (x - mean) / std)"),
        ("minmax_scale", "Min-Max Scale", "Scale features to [0, 1] range using min-max normalization (x = (x - min) / (max - min))"),
    ],
    "Encoding": [
        ("one_hot_encode", "One-Hot Encode", "Convert categorical columns to binary indicators (one column per category). Solves multicollinearity with drop_first option."),
        ("encode_classes", "Encode Classes", "Convert categorical values to numeric labels (e.g., A→0, B→1). Use for ordinal data or label encoding."),
    ],
    "Reduction": [
        ("reduce_dimensionality", "Dimensionality Reduction", "Reduce number of features using PCA (linear), t-SNE (nonlinear), or UMAP (nonlinear)"),
    ],
}


class OperationsDialog(QDialog):
    """Dialog for building and applying data operations sequentially."""

    OPERATIONS = {
        "handle_missing_values": {
            "name": "Handle Missing Values",
            "requires_columns": False,
            "params": ["strategy"],
            "compatible_types": ["numeric", "categorical"],
        },
        "drop_columns": {
            "name": "Drop Columns",
            "requires_columns": True,
            "params": [],
            "compatible_types": ["numeric", "categorical"],
        },
        "drop_outliers": {
            "name": "Drop Outliers",
            "requires_columns": True,
            "params": ["method", "threshold"],
            "compatible_types": ["numeric"],
        },
        "drop_high_corr_features": {
            "name": "Drop High Corr Features",
            "requires_columns": False,
            "params": ["threshold"],
            "compatible_types": ["numeric"],
        },
        "standard_scale": {
            "name": "Standard Scale",
            "requires_columns": True,
            "params": [],
            "compatible_types": ["numeric"],
        },
        "minmax_scale": {
            "name": "Min-Max Scale",
            "requires_columns": True,
            "params": [],
            "compatible_types": ["numeric"],
        },
        "one_hot_encode": {
            "name": "One-Hot Encode",
            "requires_columns": True,
            "params": ["drop_first"],
            "compatible_types": ["categorical"],
        },
        "encode_classes": {
            "name": "Encode Classes",
            "requires_columns": True,
            "params": [],
            "compatible_types": ["categorical"],
        },
        "reduce_dimensionality": {
            "name": "Dimensionality Reduction",
            "requires_columns": True,
            "params": ["method", "n_components"],
            "compatible_types": ["numeric"],
        },
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Operations Builder")
        
        # Set responsive dialog size based on screen
        screen = QApplication.primaryScreen().availableGeometry()
        width = max(900, int(screen.width() * 0.75))
        height = max(600, int(screen.height() * 0.75))
        self.resize(width, height)
        self.setMinimumSize(700, 500)
        
        # Center dialog on screen
        geometry = self.frameGeometry()
        geometry.moveCenter(screen.center())
        self.move(geometry.topLeft())

        self.operations_sequence: List[Dict] = []
        self.result_df: Optional[pd.DataFrame] = None
        self.result_config: Optional[Dict] = None
        self.input_df: Optional[pd.DataFrame] = None
        self.column_types: Dict[str, str] = {}

        self._build_ui()
    
    def _get_column_types(self, df: pd.DataFrame) -> Dict[str, str]:
        """Determine column types: numeric or categorical."""
        col_types = {}
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                col_types[col] = "numeric"
            else:
                col_types[col] = "categorical"
        return col_types
    
    def _is_operation_compatible(self, op_id: str, column_types: Dict[str, str]) -> Tuple[bool, str]:
        """Check if operation is compatible with column types in dataset."""
        op_info = self.OPERATIONS.get(op_id, {})
        compatible_types = op_info.get("compatible_types", [])
        
        if not compatible_types:
            return True, ""
        
        # Check if dataset has at least one compatible column type
        has_compatible = not op_info.get("requires_columns", False) or any(
            ct in compatible_types for ct in column_types.values()
        )
        
        if not has_compatible:
            incompatible_reason = f"Requires {' or '.join(compatible_types)} columns"
            return False, incompatible_reason
        
        return True, ""

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Top: operations list with groups
        ops_label = QLabel("Available Operations:")
        layout.addWidget(ops_label)

        self.operations_list = QListWidget()
        self.operations_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.operations_list.itemDoubleClicked.connect(self._on_operation_double_clicked)
        
        # Populate operations grouped by category
        for group_name, operations in OPERATION_GROUPS.items():
            # Add group header
            header_item = QListWidgetItem(group_name)
            header_font = QFont()
            header_font.setBold(True)
            header_font.setPointSize(10)
            header_item.setFont(header_font)
            header_item.setForeground(QColor("#51cf66"))
            header_item.setFlags(header_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.operations_list.addItem(header_item)
            
            # Add operations in group
            for op_id, op_name, op_description in operations:
                item = QListWidgetItem(f"  {op_name}")
                item.setToolTip(op_description)
                
                # Store metadata in item data
                item.setData(Qt.ItemDataRole.UserRole, {
                    "op_id": op_id,
                    "op_name": op_name,
                    "op_description": op_description,
                })
                self.operations_list.addItem(item)
            
            # Add spacing between groups
            spacing_item = QListWidgetItem()
            spacing_item.setText("")
            spacing_item.setFlags(spacing_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.operations_list.addItem(spacing_item)

        self.operations_list.setMinimumHeight(300)
        layout.addWidget(self.operations_list)

        # Middle: selected operations sequence
        seq_label = QLabel("Operations Sequence:")
        seq_label_font = QFont()
        seq_label_font.setBold(True)
        seq_label.setFont(seq_label_font)
        seq_label.setToolTip("⚠️ Order matters: encode before scaling, drop outliers before PCA, etc.")
        layout.addWidget(seq_label)

        self.sequence_table = QTableWidget()
        self.sequence_table.setColumnCount(4)
        self.sequence_table.setHorizontalHeaderLabels(
            ["#", "Operation", "Configuration", "Actions"]
        )
        self.sequence_table.horizontalHeader().setStretchLastSection(False)
        self.sequence_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents  # Number
        )
        self.sequence_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch  # Operation name
        )
        self.sequence_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents  # Configuration
        )
        self.sequence_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        # Disable drag-drop - we'll use buttons instead
        self.sequence_table.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)

        layout.addWidget(self.sequence_table)

        # Buttons
        button_layout = QHBoxLayout()

        add_btn = QPushButton("Add Operation")
        add_btn.setToolTip("Single-click an operation and click here, or double-click to add directly")
        add_btn.clicked.connect(self._add_operation)

        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self._clear_operations)

        button_layout.addWidget(add_btn)
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
        self.column_types = self._get_column_types(df)
        
        # Update operation compatibility indicators
        self._update_operation_compatibility()
    
    def _update_operation_compatibility(self):
        """Update which operations are enabled/disabled based on column types."""
        if not self.column_types:
            return
        
        for i in range(self.operations_list.count()):
            item = self.operations_list.item(i)
            if not item:
                continue
            
            data = item.data(Qt.ItemDataRole.UserRole)
            if not data:
                continue
            
            op_id = data.get("op_id")
            if not op_id:
                continue
            
            is_compatible, reason = self._is_operation_compatible(op_id, self.column_types)
            
            if not is_compatible:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                item.setForeground(QColor("#888888"))
                original_tooltip = data.get("op_description", "")
                item.setToolTip(f"{original_tooltip}\n\n⚠️ Not compatible: {reason}")
            else:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEnabled)
                item.setForeground(QColor("#e0e0e0"))
                item.setToolTip(data.get("op_description", ""))
    
    def _on_operation_double_clicked(self, item: QListWidgetItem):
        """Handle double-click on operation to add it directly."""
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        op_id = data.get("op_id")
        if not op_id:
            return
        
        # Check compatibility
        is_compatible, reason = self._is_operation_compatible(op_id, self.column_types)
        if not is_compatible:
            QMessageBox.warning(self, "Incompatible Operation", 
                              f"Cannot add this operation:\n{reason}")
            return
        
        # Show configuration dialog
        config = self._configure_operation(op_id)
        if config is None:
            return

        # Add to sequence
        self.operations_sequence.append({
            "operation": op_id,
            "config": config,
        })

        self._update_sequence_table()

    def _add_operation(self):
        """Add a new operation to the sequence."""
        current_row = self.operations_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select an operation.")
            return
        
        item = self.operations_list.currentItem()
        data = item.data(Qt.ItemDataRole.UserRole) if item else None
        
        if not data:
            QMessageBox.warning(self, "Warning", "Please select an operation (not a header).")
            return
        
        op_id = data.get("op_id")
        if not op_id:
            QMessageBox.warning(self, "Warning", "Please select an operation (not a header).")
            return
        
        # Check compatibility first
        is_compatible, reason = self._is_operation_compatible(op_id, self.column_types)
        if not is_compatible:
            QMessageBox.warning(self, "Incompatible Operation", 
                              f"Cannot add this operation:\n{reason}")
            return
        
        operation_info = self.OPERATIONS[op_id]

        # Show configuration dialog
        config = self._configure_operation(op_id)
        if config is None:
            return

        # Add to sequence
        self.operations_sequence.append({
            "operation": op_id,
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

        # Handle dimensionality reduction parameters
        if operation_id == "reduce_dimensionality":
            # Method selection for dimensionality reduction
            dr_methods = ["pca", "tsne", "umap"]
            method, ok = self._select_from_list(
                dr_methods, "Select Dimensionality Reduction Method:"
            )
            if not ok:
                return None
            config["method"] = method
            
            # n_components selection
            max_components = len(config.get("columns", [1]))
            n_components, ok = QInputDialog.getInt(
                self,
                "Number of Components",
                f"Number of dimensions to reduce to (1-{max_components}):",
                2,
                1,
                max_components,
                1,
            )
            if not ok:
                return None
            config["n_components"] = n_components

        if operation_id == "drop_outliers" and "method" in operation_info["params"]:
            methods = ["iqr", "zscore"]
            method, ok = self._select_from_list(
                methods, "Select Outlier Detection Method:"
            )
            if not ok:
                return None
            config["method"] = method 

        return config

    def _select_columns(self, columns: List[str]) -> Optional[List[str]]:
        """Show a dialog to select multiple columns with search and type badges."""
        # Create a simple dialog with minimal chrome (no window dressing)
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Columns")
        dialog.resize(450, 400)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowType.WindowMaximizeButtonHint & ~Qt.WindowType.WindowMinimizeButtonHint)
        
        # Use the improved column selector panel
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        
        selector = ColumnSelectorPanel(columns, self.column_types, dialog)
        layout.addWidget(selector)
        
        # Connect OK/Cancel buttons to dialog
        def on_ok_clicked():
            if selector.accepted:
                dialog.accept()
        
        def on_cancel_clicked():
            dialog.reject()
        
        selector.ok_btn.clicked.connect(on_ok_clicked)
        selector.cancel_btn.clicked.connect(on_cancel_clicked)
        
        if dialog.exec() == QDialog.Accepted:
            return selector.get_selected_columns()
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

    def _on_rows_moved(self):
        """No longer needed - drag-drop disabled."""
        pass
    
    def _move_operation_up(self, idx: int):
        """Move operation up in the sequence."""
        if idx > 0:
            self.operations_sequence[idx], self.operations_sequence[idx - 1] = \
                self.operations_sequence[idx - 1], self.operations_sequence[idx]
            self._update_sequence_table()
            # Select the moved row
            self.sequence_table.selectRow(idx - 1)
    
    def _move_operation_down(self, idx: int):
        """Move operation down in the sequence."""
        if idx < len(self.operations_sequence) - 1:
            self.operations_sequence[idx], self.operations_sequence[idx + 1] = \
                self.operations_sequence[idx + 1], self.operations_sequence[idx]
            self._update_sequence_table()
            # Select the moved row
            self.sequence_table.selectRow(idx + 1)
    
    def _update_sequence_table(self):
        """Update the operations sequence table."""
        self.sequence_table.setRowCount(len(self.operations_sequence))

        for idx, op in enumerate(self.operations_sequence):
            op_id = op["operation"]
            op_info = self.OPERATIONS[op_id]

            # Column 0: Number
            num_item = QTableWidgetItem(str(idx + 1))
            num_item.setFlags(num_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.sequence_table.setItem(idx, 0, num_item)

            # Column 1: Operation name
            name_item = QTableWidgetItem(op_info["name"])
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.sequence_table.setItem(idx, 1, name_item)

            # Column 2: Configuration
            config_str = self._format_config(op["config"])
            config_item = QTableWidgetItem(config_str)
            config_item.setFlags(config_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.sequence_table.setItem(idx, 2, config_item)

            # Column 3: Actions buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            actions_layout.setSpacing(4)
            
            # Move up button
            up_btn = QPushButton("↑")
            up_btn.setMaximumWidth(30)
            up_btn.setToolTip("Move up")
            up_btn.setEnabled(idx > 0)
            up_btn.clicked.connect(lambda checked, i=idx: self._move_operation_up(i))
            
            # Move down button
            down_btn = QPushButton("↓")
            down_btn.setMaximumWidth(30)
            down_btn.setToolTip("Move down")
            down_btn.setEnabled(idx < len(self.operations_sequence) - 1)
            down_btn.clicked.connect(lambda checked, i=idx: self._move_operation_down(i))
            
            # Remove button
            remove_btn = QPushButton("Remove")
            remove_btn.setMaximumWidth(70)
            remove_btn.clicked.connect(lambda checked, i=idx: self._remove_operation_at(i))
            
            actions_layout.addWidget(up_btn)
            actions_layout.addWidget(down_btn)
            actions_layout.addWidget(remove_btn)
            
            self.sequence_table.setCellWidget(idx, 3, actions_widget)

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
            # Run operations synchronously
            preview_df = self.input_df.copy()
            for op in self.operations_sequence:
                preview_df, _ = self._apply_operation(preview_df, op)
            
            # Show preview result
            msg = f"Preview Result:\n"
            msg += f"Shape: {preview_df.shape}\n"
            msg += f"Columns: {', '.join(preview_df.columns.tolist()[:5])}"
            if len(preview_df.columns) > 5:
                msg += f" ... ({len(preview_df.columns)} total)"
            
            QMessageBox.information(self, "Preview", msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error during preview:\n\n{str(e)}")

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
        elif operation_id == "reduce_dimensionality":
            return preprocessing.reduce_dimensionality(
                df,
                columns=config["columns"],
                method=config.get("method", "pca"),
                n_components=config.get("n_components", 2),
            )
        else:
            raise ValueError(f"Unknown operation: {operation_id}")

    def _save_version(self):
        """Apply operations and save as new version."""
        if not self.operations_sequence:
            QMessageBox.information(self, "Info", "No operations to apply.")
            return

        try:
            # Run operations synchronously
            result_df = self.input_df.copy()
            result_config = []
            
            for op in self.operations_sequence:
                result_df, op_config = self._apply_operation(result_df, op)
                result_config.append(op_config)
            
            # Store results
            self.result_df = result_df
            self.result_config = result_config
            
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
                self, "Error", f"Error applying operations:\n\n{str(e)}"
            )
    
    def get_results(self) -> Tuple[Optional[pd.DataFrame], Optional[Dict]]:
        """Get the resulting dataframe and operation config."""
        return self.result_df, self.result_config
