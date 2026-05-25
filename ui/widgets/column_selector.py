# ui/widgets/column_selector.py

from typing import List, Optional, Dict
import pandas as pd

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLineEdit,
    QMessageBox,
    QLabel,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont


class ColumnSelectorPanel(QWidget):
    """
    Inline column selector panel with search, type badges, and select all/deselect all.
    More suitable for pipeline tools than modal dialogs.
    """
    
    def __init__(self, columns: List[str], column_types: Optional[Dict[str, str]] = None, parent=None):
        """
        Initialize the column selector.
        
        Args:
            columns: List of column names
            column_types: Dict mapping column names to types (numeric/categorical)
            parent: Parent widget
        """
        super().__init__(parent)
        self.columns = columns
        self.column_types = column_types or {col: "unknown" for col in columns}
        self.selected_columns = []
        self._build_ui()
    
    def _get_type_badge(self, col: str) -> str:
        """Get a short type badge for the column."""
        col_type = self.column_types.get(col, "unknown")
        
        if col_type == "numeric":
            return "num"
        elif col_type == "categorical":
            return "cat"
        else:
            return "?"
    
    def _get_type_color(self, col: str) -> QColor:
        """Get color for type badge."""
        col_type = self.column_types.get(col, "unknown")
        
        if col_type == "numeric":
            return QColor("#5b7cfa")  # Blue
        elif col_type == "categorical":
            return QColor("#51cf66")  # Green
        else:
            return QColor("#888888")  # Gray
    
    def _build_ui(self):
        """Build the column selector UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Title
        title = QLabel("Выберите столбцы:")
        title_font = QFont()
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Search field
        search_layout = QHBoxLayout()
        search_label = QLabel("Поиск:")
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Фильтр столбцов...")
        self.search_field.textChanged.connect(self._filter_columns)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_field)
        layout.addLayout(search_layout)
        
        # Column list
        self.list_widget = QListWidget()
        self._populate_list()
        layout.addWidget(self.list_widget)
        
        # Control buttons layout
        control_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Выбрать все")
        select_all_btn.setMaximumWidth(100)
        select_all_btn.clicked.connect(self._select_all)
        
        deselect_all_btn = QPushButton("Снять выбор")
        deselect_all_btn.setMaximumWidth(100)
        deselect_all_btn.clicked.connect(self._deselect_all)
        
        control_layout.addWidget(select_all_btn)
        control_layout.addWidget(deselect_all_btn)
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.setMinimumWidth(80)
        self.ok_btn.clicked.connect(self._on_ok)
        
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setMinimumWidth(80)
        self.cancel_btn.clicked.connect(self._on_cancel)
        
        action_layout.addStretch()
        action_layout.addWidget(self.ok_btn)
        action_layout.addWidget(self.cancel_btn)
        layout.addLayout(action_layout)
        
        # Result flag
        self.accepted = False
    
    def _populate_list(self):
        """Populate the list widget with columns and type badges."""
        self.list_widget.clear()
        
        for col in self.columns:
            # Create item with column name and type badge
            type_badge = self._get_type_badge(col)
            item_text = f"{col}  [{type_badge}]"
            
            item = QListWidgetItem(item_text)
            item.setCheckState(Qt.CheckState.Unchecked)
            
            # Store original column name in data
            item.setData(Qt.ItemDataRole.UserRole, col)
            
            # Style type badge color
            badge_color = self._get_type_color(col)
            item.setForeground(QColor("#e0e0e0"))
            
            self.list_widget.addItem(item)
    
    def _filter_columns(self, search_text: str):
        """Filter columns based on search text."""
        search_lower = search_text.lower()
        
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            col_name = item.data(Qt.ItemDataRole.UserRole)
            
            # Show item if search text is in column name or type badge
            type_badge = self._get_type_badge(col_name)
            should_show = (
                search_lower in col_name.lower() or 
                search_lower in type_badge.lower()
            )
            
            self.list_widget.setRowHidden(i, not should_show)
    
    def _select_all(self):
        """Select all visible columns."""
        for i in range(self.list_widget.count()):
            if not self.list_widget.isRowHidden(i):
                item = self.list_widget.item(i)
                item.setCheckState(Qt.CheckState.Checked)
    
    def _deselect_all(self):
        """Deselect all columns."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.CheckState.Unchecked)
    
    def _on_ok(self):
        """Handle OK button click."""
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                col_name = item.data(Qt.ItemDataRole.UserRole)
                selected.append(col_name)
        
        if not selected:
            QMessageBox.warning(self, "Предупреждение", "Выберите хотя бы один столбец.")
            return
        
        self.selected_columns = selected
        self.accepted = True
        
    def _on_cancel(self):
        """Handle Cancel button click."""
        self.accepted = False
    
    def get_selected_columns(self) -> Optional[List[str]]:
        """Get the selected columns if OK was clicked, None if cancelled."""
        if self.accepted:
            return self.selected_columns
        return None
