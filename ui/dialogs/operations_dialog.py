# ui/dialogs/operations_dialog.py

from typing import List, Dict, Tuple, Optional
import pandas as pd

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
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
    "Очистка": [
        ("handle_missing_values", "Обработка пропущенных значений", "Заполнение или удаление строк с пропущенными данными: среднее, медиана, мода или удаление"),
        ("drop_columns", "Удаление столбцов", "Удалить указанные столбцы из набора данных"),
        ("drop_outliers", "Удаление выбросов", "Удалить строки с выбросами методом IQR или Z-оценки"),
        ("drop_high_corr_features", "Удаление высококоррелированных признаков", "Удалить сильно коррелирующие признаки (по умолчанию: корреляция >0.95). Используется коэффициент корреляции Пирсона."),
    ],
    "Масштабирование": [
        ("standard_scale", "Стандартное масштабирование", "Нормализация признаков до среднего=0, std=1 методом z-оценки (x = (x - среднее) / std)"),
        ("minmax_scale", "Min-Max масштабирование", "Масштабирование признаков в диапазон [0, 1] методом min-max (x = (x - min) / (max - min))"),
    ],
    "Кодирование": [
        ("one_hot_encode", "One-Hot кодирование", "Преобразование категориальных столбцов в бинарные индикаторы (один столбец на категорию). Решает мультиколлинеарность с опцией drop_first."),
        ("encode_classes", "Кодирование классов", "Преобразование категориальных значений в числовые метки (например, A→0, B→1). Используется для порядковых данных или кодирования меток."),
    ],
    "Балансировка": [
        ("oversample_classes", "Балансировка классов (oversample)", "Создать новую версию датасета с выбранной пропорцией классов через повторную выборку или синтетическую генерацию."),
    ],
    "Снижение размерности": [
        ("reduce_dimensionality", "Снижение размерности", "Уменьшение числа признаков методами PCA (линейный), t-SNE (нелинейный) или UMAP (нелинейный)"),
    ],
}


class OperationsDialog(QDialog):
    """Диалог для построения и последовательного применения операций над данными."""

    OPERATIONS = {
        "handle_missing_values": {
            "name": "Обработка пропущенных значений",
            "requires_columns": False,
            "params": ["strategy"],
            "compatible_types": ["numeric", "categorical"],
        },
        "drop_columns": {
            "name": "Удаление столбцов",
            "requires_columns": True,
            "params": [],
            "compatible_types": ["numeric", "categorical"],
        },
        "drop_outliers": {
            "name": "Удаление выбросов",
            "requires_columns": True,
            "params": ["method", "threshold"],
            "compatible_types": ["numeric"],
        },
        "drop_high_corr_features": {
            "name": "Удаление высококоррелированных признаков",
            "requires_columns": False,
            "params": ["threshold"],
            "compatible_types": ["numeric"],
        },
        "standard_scale": {
            "name": "Стандартное масштабирование",
            "requires_columns": True,
            "params": [],
            "compatible_types": ["numeric"],
        },
        "minmax_scale": {
            "name": "Min-Max масштабирование",
            "requires_columns": True,
            "params": [],
            "compatible_types": ["numeric"],
        },
        "one_hot_encode": {
            "name": "One-Hot кодирование",
            "requires_columns": True,
            "params": ["drop_first"],
            "compatible_types": ["categorical"],
        },
        "encode_classes": {
            "name": "Кодирование классов",
            "requires_columns": True,
            "params": [],
            "compatible_types": ["categorical"],
        },
        "reduce_dimensionality": {
            "name": "Снижение размерности",
            "requires_columns": True,
            "params": ["method", "n_components"],
            "compatible_types": ["numeric"],
        },
        "oversample_classes": {
            "name": "Балансировка классов (oversample)",
            "requires_columns": False,
            "params": ["class_column", "target_proportions", "oversample_method"],
            "compatible_types": ["numeric", "categorical"],
        },
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Конструктор операций")
        
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
        """Определить типы столбцов: числовой или категориальный."""
        col_types = {}
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                col_types[col] = "numeric"
            else:
                col_types[col] = "categorical"
        return col_types
    
    def _is_operation_compatible(self, op_id: str, column_types: Dict[str, str]) -> Tuple[bool, str]:
        """Проверить совместимость операции с типами столбцов набора данных."""
        op_info = self.OPERATIONS.get(op_id, {})
        compatible_types = op_info.get("compatible_types", [])
        
        if not compatible_types:
            return True, ""
        
        has_compatible = not op_info.get("requires_columns", False) or any(
            ct in compatible_types for ct in column_types.values()
        )
        
        if not has_compatible:
            incompatible_reason = f"Требуются столбцы типа: {' или '.join(compatible_types)}"
            return False, incompatible_reason
        
        return True, ""

    def _build_ui(self):
        layout = QVBoxLayout(self)

        ops_label = QLabel("Доступные операции:")
        layout.addWidget(ops_label)

        self.operations_list = QListWidget()
        self.operations_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.operations_list.itemDoubleClicked.connect(self._on_operation_double_clicked)
        
        for group_name, operations in OPERATION_GROUPS.items():
            header_item = QListWidgetItem(group_name)
            header_font = QFont()
            header_font.setBold(True)
            header_font.setPointSize(10)
            header_item.setFont(header_font)
            header_item.setForeground(QColor("#51cf66"))
            header_item.setFlags(header_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.operations_list.addItem(header_item)
            
            for op_id, op_name, op_description in operations:
                item = QListWidgetItem(f"  {op_name}")
                item.setToolTip(op_description)
                item.setData(Qt.ItemDataRole.UserRole, {
                    "op_id": op_id,
                    "op_name": op_name,
                    "op_description": op_description,
                })
                self.operations_list.addItem(item)
            
            spacing_item = QListWidgetItem()
            spacing_item.setText("")
            spacing_item.setFlags(spacing_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.operations_list.addItem(spacing_item)

        self.operations_list.setMinimumHeight(300)
        layout.addWidget(self.operations_list)

        seq_label = QLabel("Последовательность операций:")
        seq_label_font = QFont()
        seq_label_font.setBold(True)
        seq_label.setFont(seq_label_font)
        seq_label.setToolTip("⚠️ Порядок важен: кодирование до масштабирования, удаление выбросов до PCA и т.д.")
        layout.addWidget(seq_label)

        self.sequence_table = QTableWidget()
        self.sequence_table.setColumnCount(4)
        self.sequence_table.setHorizontalHeaderLabels(
            ["№", "Операция", "Конфигурация", "Действия"]
        )
        self.sequence_table.horizontalHeader().setStretchLastSection(False)
        self.sequence_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.sequence_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.sequence_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.sequence_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.sequence_table.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)

        layout.addWidget(self.sequence_table)

        button_layout = QHBoxLayout()

        add_btn = QPushButton("Добавить операцию")
        add_btn.setToolTip("Выберите операцию одним кликом и нажмите сюда, или дважды кликните для добавления")
        add_btn.clicked.connect(self._add_operation)

        clear_btn = QPushButton("Очистить всё")
        clear_btn.clicked.connect(self._clear_operations)

        button_layout.addWidget(add_btn)
        button_layout.addWidget(clear_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        final_layout = QHBoxLayout()

        apply_preview_btn = QPushButton("Предпросмотр")
        apply_preview_btn.clicked.connect(self._preview_operations)

        save_btn = QPushButton("Применить и сохранить версию")
        save_btn.clicked.connect(self._save_version)

        final_layout.addStretch()
        final_layout.addWidget(apply_preview_btn)
        final_layout.addWidget(save_btn)

        layout.addLayout(final_layout)

    def set_dataframe(self, df: pd.DataFrame):
        """Установить входной датафрейм для операций."""
        self.input_df = df.copy()
        self.column_types = self._get_column_types(df)
        self._update_operation_compatibility()
    
    def _update_operation_compatibility(self):
        """Обновить доступность операций на основе типов столбцов."""
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
                item.setToolTip(f"{original_tooltip}\n\n⚠️ Несовместима: {reason}")
            else:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEnabled)
                item.setForeground(QColor("#e0e0e0"))
                item.setToolTip(data.get("op_description", ""))
    
    def _on_operation_double_clicked(self, item: QListWidgetItem):
        """Обработка двойного клика по операции для её добавления."""
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        op_id = data.get("op_id")
        if not op_id:
            return
        
        is_compatible, reason = self._is_operation_compatible(op_id, self.column_types)
        if not is_compatible:
            QMessageBox.warning(self, "Несовместимая операция", 
                              f"Невозможно добавить операцию:\n{reason}")
            return
        
        config = self._configure_operation(op_id)
        if config is None:
            return

        self.operations_sequence.append({
            "operation": op_id,
            "config": config,
        })

        self._update_sequence_table()

    def _add_operation(self):
        """Добавить новую операцию в последовательность."""
        current_row = self.operations_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Предупреждение", "Выберите операцию.")
            return
        
        item = self.operations_list.currentItem()
        data = item.data(Qt.ItemDataRole.UserRole) if item else None
        
        if not data:
            QMessageBox.warning(self, "Предупреждение", "Выберите операцию (не заголовок).")
            return
        
        op_id = data.get("op_id")
        if not op_id:
            QMessageBox.warning(self, "Предупреждение", "Выберите операцию (не заголовок).")
            return
        
        is_compatible, reason = self._is_operation_compatible(op_id, self.column_types)
        if not is_compatible:
            QMessageBox.warning(self, "Несовместимая операция", 
                              f"Невозможно добавить операцию:\n{reason}")
            return
        
        operation_info = self.OPERATIONS[op_id]

        config = self._configure_operation(op_id)
        if config is None:
            return

        self.operations_sequence.append({
            "operation": op_id,
            "config": config,
        })

        self._update_sequence_table()

    def _configure_operation(self, operation_id: str) -> Optional[Dict]:
        """Показать диалог настройки для выбранной операции."""
        operation_info = self.OPERATIONS[operation_id]
        config = {}

        if operation_id == "oversample_classes":
            return self._configure_oversample_classes()

        if operation_info["requires_columns"]:
            columns = self.input_df.columns.tolist()

            if operation_id == "encode_classes":
                col, ok = self._select_single_column(columns)
                if not ok:
                    return None
                config["column"] = col
            else:
                cols = self._select_columns(columns)
                if cols is None:
                    return None
                config["columns"] = cols

        if "strategy" in operation_info["params"]:
            strategies = ["mean", "median", "mode", "drop_rows", "drop_columns"]
            strategy, ok = self._select_from_list(
                strategies, "Выберите стратегию обработки пропущенных значений:"
            )
            if not ok:
                return None
            config["strategy"] = strategy

        if "threshold" in operation_info["params"]:
            threshold, ok = self._get_float_input("Порог:", 0.8)
            if not ok:
                return None
            config["threshold"] = threshold

        if "drop_first" in operation_info["params"]:
            drop_first = self._get_bool_input("Удалить первую категорию?")
            config["drop_first"] = drop_first

        if operation_id == "reduce_dimensionality":
            dr_methods = ["pca", "tsne", "umap"]
            method, ok = self._select_from_list(
                dr_methods, "Выберите метод снижения размерности:"
            )
            if not ok:
                return None
            config["method"] = method
            
            max_components = len(config.get("columns", [1]))
            n_components, ok = QInputDialog.getInt(
                self,
                "Количество компонент",
                f"Число измерений для снижения (1-{max_components}):",
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
                methods, "Выберите метод обнаружения выбросов:"
            )
            if not ok:
                return None
            config["method"] = method 

        return config

    def _configure_oversample_classes(self) -> Optional[Dict]:
        """Показать настройку пропорций классов для oversample."""
        if self.input_df is None or self.input_df.empty:
            QMessageBox.warning(self, "Предупреждение", "Нет данных для балансировки.")
            return None

        columns = self.input_df.columns.tolist()
        class_column, ok = self._select_single_column(columns)
        if not ok:
            return None

        counts = self.input_df[class_column].value_counts(dropna=False)
        if len(counts) < 2:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Для oversample нужно минимум два класса в выбранном столбце.",
            )
            return None

        dialog = QDialog(self)
        dialog.setWindowTitle("Балансировка классов (oversample)")
        dialog.resize(460, 360)

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(f"Столбец класса: {class_column}"))

        method_combo = QComboBox()
        method_combo.addItem("Повторная выборка из исходного датасета", "sample")
        method_combo.addItem("Синтетическая генерация", "synthesis")

        synthesis_model_combo = QComboBox()
        synthesis_model_combo.addItem("Gaussian Copula", "gaussian_copula")
        synthesis_model_combo.addItem("CTGAN", "ctgan")
        synthesis_model_combo.addItem("TVAE", "tvae")
        synthesis_model_combo.setEnabled(False)

        method_combo.currentIndexChanged.connect(
            lambda: synthesis_model_combo.setEnabled(method_combo.currentData() == "synthesis")
        )

        form = QFormLayout()
        form.addRow("Метод", method_combo)
        form.addRow("Модель синтеза", synthesis_model_combo)
        layout.addLayout(form)

        proportions_label = QLabel("Целевая пропорция классов, %:")
        layout.addWidget(proportions_label)

        proportions_form = QFormLayout()
        spinboxes = {}
        total_count = len(self.input_df)
        for class_value, count in counts.items():
            spinbox = QDoubleSpinBox()
            spinbox.setRange(0.0, 100.0)
            spinbox.setDecimals(2)
            spinbox.setSingleStep(1.0)
            spinbox.setValue(round((count / total_count) * 100, 2))
            spinboxes[class_value] = spinbox
            proportions_form.addRow(f"{class_value} ({count})", spinbox)
        layout.addLayout(proportions_form)

        buttons_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Отмена")
        buttons_layout.addStretch()
        buttons_layout.addWidget(ok_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)

        def on_ok_clicked():
            total = sum(spinbox.value() for spinbox in spinboxes.values())
            if total <= 0:
                QMessageBox.warning(dialog, "Предупреждение", "Сумма пропорций должна быть больше 0.")
                return

            zero_classes = [
                str(class_value)
                for class_value, spinbox in spinboxes.items()
                if spinbox.value() <= 0
            ]
            if zero_classes:
                QMessageBox.warning(
                    dialog,
                    "Предупреждение",
                    "Oversample не удаляет исходные строки, поэтому доля существующего класса не может быть 0: "
                    + ", ".join(zero_classes),
                )
                return

            dialog.accept()

        ok_btn.clicked.connect(on_ok_clicked)
        cancel_btn.clicked.connect(dialog.reject)

        if dialog.exec() != QDialog.Accepted:
            return None

        return {
            "class_column": class_column,
            "target_proportions": {
                str(class_value): spinbox.value()
                for class_value, spinbox in spinboxes.items()
            },
            "method": method_combo.currentData(),
            "synthesis_model": synthesis_model_combo.currentData(),
        }

    def _select_columns(self, columns: List[str]) -> Optional[List[str]]:
        """Показать диалог выбора нескольких столбцов с поиском и типовыми метками."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Выбор столбцов")
        dialog.resize(450, 400)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowType.WindowMaximizeButtonHint & ~Qt.WindowType.WindowMinimizeButtonHint)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        
        selector = ColumnSelectorPanel(columns, self.column_types, dialog)
        layout.addWidget(selector)
        
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
        """Показать диалог выбора одного столбца."""
        col, ok = QInputDialog.getItem(
            self, "Выбор столбца", "Выберите столбец:", columns, 0, False
        )
        return col, ok

    def _select_from_list(
        self, items: List[str], label: str
    ) -> Tuple[str, bool]:
        """Показать диалог выбора из списка элементов."""
        item, ok = QInputDialog.getItem(
            self, "Выбор параметра", label, items, 0, False
        )
        return item, ok

    def _get_float_input(self, label: str, default: float = 0.5) -> Tuple[float, bool]:
        """Показать диалог ввода числа с плавающей точкой."""
        value, ok = QInputDialog.getDouble(
            self, "Ввод значения", label, default, 0.0, 1.0, 2
        )
        return value, ok

    def _get_bool_input(self, label: str) -> bool:
        """Показать диалог для булевого ввода."""
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Подтверждение")
        msg_box.setText(label)
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return msg_box.exec() == QMessageBox.StandardButton.Yes

    def _remove_operation(self):
        """Удалить выбранную операцию из последовательности."""
        current_row = self.sequence_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Предупреждение", "Выберите операцию для удаления.")
            return

        del self.operations_sequence[current_row]
        self._update_sequence_table()

    def _clear_operations(self):
        """Очистить все операции."""
        reply = QMessageBox.question(
            self, "Подтверждение", "Очистить все операции?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.operations_sequence = []
            self._update_sequence_table()

    def _on_rows_moved(self):
        """Не используется — перетаскивание отключено."""
        pass
    
    def _move_operation_up(self, idx: int):
        """Переместить операцию вверх по последовательности."""
        if idx > 0:
            self.operations_sequence[idx], self.operations_sequence[idx - 1] = \
                self.operations_sequence[idx - 1], self.operations_sequence[idx]
            self._update_sequence_table()
            self.sequence_table.selectRow(idx - 1)
    
    def _move_operation_down(self, idx: int):
        """Переместить операцию вниз по последовательности."""
        if idx < len(self.operations_sequence) - 1:
            self.operations_sequence[idx], self.operations_sequence[idx + 1] = \
                self.operations_sequence[idx + 1], self.operations_sequence[idx]
            self._update_sequence_table()
            self.sequence_table.selectRow(idx + 1)
    
    def _update_sequence_table(self):
        """Обновить таблицу последовательности операций."""
        self.sequence_table.setRowCount(len(self.operations_sequence))

        for idx, op in enumerate(self.operations_sequence):
            op_id = op["operation"]
            op_info = self.OPERATIONS[op_id]

            num_item = QTableWidgetItem(str(idx + 1))
            num_item.setFlags(num_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.sequence_table.setItem(idx, 0, num_item)

            name_item = QTableWidgetItem(op_info["name"])
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.sequence_table.setItem(idx, 1, name_item)

            config_str = self._format_config(op["config"])
            config_item = QTableWidgetItem(config_str)
            config_item.setFlags(config_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.sequence_table.setItem(idx, 2, config_item)

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            actions_layout.setSpacing(4)
            
            up_btn = QPushButton("↑")
            up_btn.setMaximumWidth(30)
            up_btn.setToolTip("Переместить вверх")
            up_btn.setEnabled(idx > 0)
            up_btn.clicked.connect(lambda checked, i=idx: self._move_operation_up(i))
            
            down_btn = QPushButton("↓")
            down_btn.setMaximumWidth(30)
            down_btn.setToolTip("Переместить вниз")
            down_btn.setEnabled(idx < len(self.operations_sequence) - 1)
            down_btn.clicked.connect(lambda checked, i=idx: self._move_operation_down(i))
            
            remove_btn = QPushButton("Удалить")
            remove_btn.setMaximumWidth(80)
            remove_btn.clicked.connect(lambda checked, i=idx: self._remove_operation_at(i))
            
            actions_layout.addWidget(up_btn)
            actions_layout.addWidget(down_btn)
            actions_layout.addWidget(remove_btn)
            
            self.sequence_table.setCellWidget(idx, 3, actions_widget)

    def _remove_operation_at(self, idx: int):
        """Удалить операцию по конкретному индексу."""
        if 0 <= idx < len(self.operations_sequence):
            del self.operations_sequence[idx]
            self._update_sequence_table()

    def _format_config(self, config: Dict) -> str:
        """Форматировать словарь конфигурации в читаемую строку."""
        parts = []
        for key, value in config.items():
            if isinstance(value, list):
                value_str = ", ".join(value[:3])
                if len(value) > 3:
                    value_str += "..."
            elif isinstance(value, dict):
                value_str = f"Словарь({len(value)} элем.)"
            else:
                value_str = str(value)
            parts.append(f"{key}: {value_str}")
        return " | ".join(parts)

    def _preview_operations(self):
        """Предпросмотр операций на датафрейме."""
        if not self.operations_sequence:
            QMessageBox.information(self, "Информация", "Нет операций для предпросмотра.")
            return

        try:
            preview_df = self.input_df.copy()
            for op in self.operations_sequence:
                preview_df, _ = self._apply_operation(preview_df, op)
            
            msg = f"Результат предпросмотра:\n"
            msg += f"Размер: {preview_df.shape}\n"
            msg += f"Столбцы: {', '.join(preview_df.columns.tolist()[:5])}"
            if len(preview_df.columns) > 5:
                msg += f" ... ({len(preview_df.columns)} всего)"
            
            QMessageBox.information(self, "Предпросмотр", msg)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при предпросмотре:\n\n{str(e)}")

    def _apply_operation(
        self, df: pd.DataFrame, op: Dict
    ) -> Tuple[pd.DataFrame, Dict]:
        """Применить одну операцию к датафрейму."""
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
        elif operation_id == "oversample_classes":
            return preprocessing.oversample_classes(
                df,
                class_column=config["class_column"],
                target_proportions=config["target_proportions"],
                method=config.get("method", "sample"),
                synthesis_model=config.get("synthesis_model", "gaussian_copula"),
            )
        else:
            raise ValueError(f"Неизвестная операция: {operation_id}")

    def _save_version(self):
        """Применить операции и сохранить как новую версию."""
        if not self.operations_sequence:
            QMessageBox.information(self, "Информация", "Нет операций для применения.")
            return

        try:
            result_df = self.input_df.copy()
            result_config = []
            
            for op in self.operations_sequence:
                result_df, op_config = self._apply_operation(result_df, op)
                result_config.append(op_config)
            
            self.result_df = result_df
            self.result_config = result_config
            
            QMessageBox.information(
                self,
                "Успешно",
                f"Операции применены успешно!\n"
                f"Размер результата: {self.result_df.shape}\n"
                f"Результат сохранён.",
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка", f"Ошибка при применении операций:\n\n{str(e)}"
            )
    
    def get_results(self) -> Tuple[Optional[pd.DataFrame], Optional[Dict]]:
        """Получить результирующий датафрейм и конфигурацию операций."""
        return self.result_df, self.result_config
