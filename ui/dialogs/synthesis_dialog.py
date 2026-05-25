from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QSpinBox,
    QDoubleSpinBox, QComboBox, QPushButton, QMessageBox, QApplication,
    QScrollArea, QWidget, QGroupBox, QFrame, QSizePolicy, QToolButton,
    QCheckBox, QInputDialog
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor
import pandas as pd
import time

from core import synthesis
from core.worker_thread import WorkerThread
from ui.dialogs.progress_dialog import ProgressDialog


# ---------------------------------------------------------------------------
# Method metadata
# ---------------------------------------------------------------------------

METHOD_META = {
    "Gaussian Copula": {
        "model_type": "gaussian_copula",
        "description": (
            "Моделирует статистические связи между столбцами с помощью копул. "
            "Предполагает, что числовые столбцы после маргинального преобразования "
            "примерно нормально распределены. Самый быстрый из трёх методов, подходит "
            "для структурированных табличных данных с умеренными корреляциями."
        ),
        "speed": "Быстро",
    },
    "CTGAN": {
        "model_type": "ctgan",
        "description": (
            "Генеративно-состязательная сеть для табличных данных. Хорошо работает "
            "со смешанными числовыми и категориальными столбцами, а также с "
            "ненормальными распределениями. Время обучения зависит от числа эпох "
            "и размера датасета, на больших данных это скорее минуты, чем секунды."
        ),
        "speed": "Медленно",
    },
    "TVAE": {
        "model_type": "tvae",
        "description": (
            "Вариационный автоэнкодер, оптимизированный для табличных данных. "
            "Кодирует строки в латентное пространство и декодирует синтетические "
            "образцы. Обычно быстрее CTGAN при сопоставимом качестве; размерность "
            "латентного пространства управляет выразительностью модели."
        ),
        "speed": "Средне",
    },
}

SPEED_COLOR = {
    "Быстро": "#51cf66",
    "Средне": "#ffd43b",
    "Медленно": "#ff6b6b",
}


# ---------------------------------------------------------------------------
# Collapsible section widget
# ---------------------------------------------------------------------------

class CollapsibleSection(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._title = title
        self._collapsed = True
        # key -> QWidget (the full row wrapper)
        self._row_widgets: dict = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header button
        self.toggle_btn = QToolButton()
        self.toggle_btn.setText(f"▶  {title}")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(False)
        self.toggle_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
                color: #b0b0b0;
                font-size: 11px;
                text-align: left;
                padding: 4px 0px;
            }
            QToolButton:hover { color: #e0e0e0; }
            QToolButton:checked { color: #5b7cfa; }
        """)
        self.toggle_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.toggle_btn.clicked.connect(self._toggle)
        outer.addWidget(self.toggle_btn)

        # Content container — VBox of row widgets
        self.content = QWidget()
        self.content.setVisible(False)
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(16, 4, 0, 4)
        self.content_layout.setSpacing(4)
        outer.addWidget(self.content)

    def _toggle(self, checked: bool):
        self._collapsed = not checked
        self.content.setVisible(checked)
        arrow = "▼" if checked else "▶"
        self.toggle_btn.setText(f"{arrow}  {self._title}")

    def add_row(self, key: str, label: str, widget: QWidget):
        """Add a labelled row identified by key. Row is hidden by default."""
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        if label:
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #b0b0b0; font-size: 10px;")
            lbl.setFixedWidth(130)
            row_layout.addWidget(lbl)

        row_layout.addWidget(widget)

        row.setVisible(False)
        self._row_widgets[key] = row
        self.content_layout.addWidget(row)

    def set_row_visible(self, key: str, visible: bool):
        row = self._row_widgets.get(key)
        if row is not None:
            row.setVisible(visible)


# ---------------------------------------------------------------------------
# Main dialog
# ---------------------------------------------------------------------------

class SynthesisDialog(QDialog):
    """Redesigned synthesis dialog with method descriptions, advanced params,
    source context, and post-synthesis quality report."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Синтез данных")
        self.setModal(True)

        screen = QApplication.primaryScreen().availableGeometry()
        width = max(560, int(screen.width() * 0.38))
        height = max(520, int(screen.height() * 0.60))
        self.resize(width, height)
        self.setMinimumSize(480, 460)

        geometry = self.frameGeometry()
        geometry.moveCenter(screen.center())
        self.move(geometry.topLeft())

        self.current_df = None
        self.result_df = None
        self.result_config = None
        self._dataset_name = None
        self._version_name = None
        self._is_active = True

        self._init_ui()
        self._on_method_changed("Gaussian Copula")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_dataframe(self, df: pd.DataFrame) -> None:
        self.current_df = df
        source_rows = len(df)
        self._source_rows_label.setText(
            f"Исходный датасет: {source_rows:,} строк × {len(df.columns)} столбцов"
        )
        # Default synthesized row count to match source
        self.rows_spinbox.setValue(min(source_rows, 100000))

    def set_source_info(self, dataset_name: str, version_name: str) -> None:
        self._dataset_name = dataset_name
        self._version_name = version_name
        self.setWindowTitle(f"Синтез данных - {dataset_name} > {version_name}")
        self._source_label.setText(f"Источник: {dataset_name} > {version_name}")

    def get_results(self) -> tuple:
        return self.result_df, self.result_config

    def get_parameters(self) -> dict:
        return {
            "mode": self.mode_combo.currentText(),
            "rows": self.rows_spinbox.value(),
        }

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Scroll area so content is reachable on small screens
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(12)
        scroll.setWidget(scroll_content)
        root.addWidget(scroll)

        # ── Source info ──────────────────────────────────────────────
        source_box = QFrame()
        source_box.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border: 1px solid #3a3d4a;
                border-radius: 4px;
                padding: 6px 10px;
            }
        """)
        source_box_layout = QVBoxLayout(source_box)
        source_box_layout.setContentsMargins(8, 6, 8, 6)
        source_box_layout.setSpacing(2)

        self._source_label = QLabel("Источник: -")
        self._source_label.setStyleSheet("color: #b0b0b0; font-size: 11px;")
        self._source_rows_label = QLabel("Исходный датасет: - строк")
        self._source_rows_label.setStyleSheet("color: #777777; font-size: 10px;")

        source_box_layout.addWidget(self._source_label)
        source_box_layout.addWidget(self._source_rows_label)
        layout.addWidget(source_box)

        # ── Method selector ─────────────────────────────────────────
        method_group = QGroupBox("Метод синтеза")
        method_layout = QVBoxLayout(method_group)
        method_layout.setSpacing(8)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Gaussian Copula", "CTGAN", "TVAE"])
        self.mode_combo.currentTextChanged.connect(self._on_method_changed)
        method_layout.addWidget(self.mode_combo)

        # Speed badge + description
        badge_row = QHBoxLayout()
        self._speed_label = QLabel()
        self._speed_label.setFixedWidth(60)
        self._speed_label.setAlignment(Qt.AlignCenter)
        f = self._speed_label.font()
        f.setPointSize(8)
        f.setBold(True)
        self._speed_label.setFont(f)
        badge_row.addWidget(self._speed_label)
        badge_row.addStretch()
        method_layout.addLayout(badge_row)

        self._description_label = QLabel()
        self._description_label.setWordWrap(True)
        self._description_label.setStyleSheet("color: #999999; font-size: 10px; line-height: 1.4;")
        self._description_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        method_layout.addWidget(self._description_label)

        layout.addWidget(method_group)

        # ── Advanced parameters (collapsible) ────────────────────────
        self._advanced_section = CollapsibleSection("Расширенные параметры")
        layout.addWidget(self._advanced_section)

        # CTGAN params
        self._ctgan_epochs = QSpinBox()
        self._ctgan_epochs.setRange(1, 2000)
        self._ctgan_epochs.setValue(300)

        self._ctgan_batch_size = QSpinBox()
        self._ctgan_batch_size.setRange(50, 4096)
        self._ctgan_batch_size.setValue(500)
        self._ctgan_batch_size.setSingleStep(50)

        self._ctgan_gen_lr = QDoubleSpinBox()
        self._ctgan_gen_lr.setRange(0.00001, 0.1)
        self._ctgan_gen_lr.setValue(0.0002)
        self._ctgan_gen_lr.setDecimals(5)
        self._ctgan_gen_lr.setSingleStep(0.0001)

        self._ctgan_disc_lr = QDoubleSpinBox()
        self._ctgan_disc_lr.setRange(0.00001, 0.1)
        self._ctgan_disc_lr.setValue(0.0002)
        self._ctgan_disc_lr.setDecimals(5)
        self._ctgan_disc_lr.setSingleStep(0.0001)

        # TVAE params
        self._tvae_latent_dim = QSpinBox()
        self._tvae_latent_dim.setRange(2, 512)
        self._tvae_latent_dim.setValue(128)

        self._tvae_epochs = QSpinBox()
        self._tvae_epochs.setRange(1, 2000)
        self._tvae_epochs.setValue(300)

        self._tvae_lr = QDoubleSpinBox()
        self._tvae_lr.setRange(0.00001, 0.1)
        self._tvae_lr.setValue(0.001)
        self._tvae_lr.setDecimals(5)
        self._tvae_lr.setSingleStep(0.0001)

        # Gaussian Copula params
        self._gc_enforce_bounds = QCheckBox("Соблюдать min/max границы")
        self._gc_enforce_bounds.setChecked(True)
        self._gc_enforce_bounds.setStyleSheet("color: #b0b0b0; font-size: 10px;")

        # Register all rows — shown/hidden as whole row widgets via _on_method_changed
        self._adv_rows = {
            "ctgan_epochs":    ("Эпохи",             self._ctgan_epochs),
            "ctgan_batch":     ("Размер батча",         self._ctgan_batch_size),
            "ctgan_gen_lr":    ("LR генератора",       self._ctgan_gen_lr),
            "ctgan_disc_lr":   ("LR дискриминатора",   self._ctgan_disc_lr),
            "tvae_latent":     ("Латентная размерность",  self._tvae_latent_dim),
            "tvae_epochs":     ("Эпохи",             self._tvae_epochs),
            "tvae_lr":         ("Скорость обучения",      self._tvae_lr),
            "gc_bounds":       ("",                   self._gc_enforce_bounds),
        }
        for key, (label, widget) in self._adv_rows.items():
            self._advanced_section.add_row(key, label, widget)

        # ── Row count ────────────────────────────────────────────────
        rows_group = QGroupBox("Эпохи")
        rows_form = QFormLayout(rows_group)
        rows_form.setSpacing(8)

        self.rows_spinbox = QSpinBox()
        self.rows_spinbox.setMinimum(1)
        self.rows_spinbox.setMaximum(100000)
        self.rows_spinbox.setValue(1000)
        self.rows_spinbox.setSingleStep(100)
        rows_form.addRow("Строк для генерации:", self.rows_spinbox)

        layout.addWidget(rows_group)
        layout.addStretch()

        # ── Action buttons ───────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setMinimumHeight(32)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2d3a;
                color: #b0b0b0;
                border: 1px solid #3a3d4a;
                padding: 6px 16px;
                border-radius: 3px;
            }
            QPushButton:hover { background-color: #3a3d4a; }
        """)
        self.cancel_btn.clicked.connect(self.reject)

        self.synthesize_btn = QPushButton("Синтезировать")
        self.synthesize_btn.setMinimumHeight(32)
        self.synthesize_btn.setStyleSheet("""
            QPushButton {
                background-color: #5b7cfa;
                color: white;
                border: none;
                padding: 6px 20px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #4c63d2; }
            QPushButton:disabled { background-color: #3a3d4a; color: #666; }
        """)
        self.synthesize_btn.clicked.connect(self._on_synthesize)

        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.synthesize_btn)
        root.addLayout(btn_layout)

    # ------------------------------------------------------------------
    # Method selection
    # ------------------------------------------------------------------

    def _on_method_changed(self, method: str):
        meta = METHOD_META.get(method, {})

        # Description
        self._description_label.setText(meta.get("description", ""))

        # Speed badge
        speed = meta.get("speed", "")
        color = SPEED_COLOR.get(speed, "#888888")
        self._speed_label.setText(speed)
        self._speed_label.setStyleSheet(f"""
            QLabel {{
                background-color: {color}22;
                color: {color};
                border: 1px solid {color}66;
                border-radius: 3px;
                padding: 2px 6px;
            }}
        """)

        # Show/hide advanced param rows
        ctgan_keys = {"ctgan_epochs", "ctgan_batch", "ctgan_gen_lr", "ctgan_disc_lr"}
        tvae_keys = {"tvae_latent", "tvae_epochs", "tvae_lr"}
        gc_keys = {"gc_bounds"}

        if not hasattr(self, '_adv_rows'):
            return

        for key in self._adv_rows:
            if method == "CTGAN":
                self._advanced_section.set_row_visible(key, key in ctgan_keys)
            elif method == "TVAE":
                self._advanced_section.set_row_visible(key, key in tvae_keys)
            elif method == "Gaussian Copula":
                self._advanced_section.set_row_visible(key, key in gc_keys)
            else:
                self._advanced_section.set_row_visible(key, False)

    # ------------------------------------------------------------------
    # Synthesis
    # ------------------------------------------------------------------

    def _build_model_kwargs(self) -> dict:
        method = self.mode_combo.currentText()
        kwargs = {}
        if method == "CTGAN":
            kwargs["epochs"] = self._ctgan_epochs.value()
            kwargs["batch_size"] = self._ctgan_batch_size.value()
            kwargs["generator_lr"] = self._ctgan_gen_lr.value()
            kwargs["discriminator_lr"] = self._ctgan_disc_lr.value()
        elif method == "TVAE":
            kwargs["epochs"] = self._tvae_epochs.value()
        # Gaussian Copula min/max enforcement is handled by SDV by default;
        # no kwarg needed unless explicitly turning it off.
        return kwargs

    def _on_synthesize(self) -> None:
        if self.current_df is None:
            QMessageBox.warning(self, "Ошибка", "Датафрейм не загружен.")
            return

        num_rows = self.rows_spinbox.value()
        if num_rows < 1:
            QMessageBox.warning(self, "Проверка", "Количество строк должно быть не меньше 1.")
            return

        mode = self.mode_combo.currentText()
        model_type = METHOD_META[mode]["model_type"]
        model_kwargs = self._build_model_kwargs()

        self.worker = WorkerThread(
            func=synthesis.synthesize,
            kwargs={
                "df": self.current_df,
                "num_rows": num_rows,
                "model_type": model_type,
                "evaluate": True,
                **model_kwargs,
            }
        )

        self.progress_dialog = ProgressDialog(
            f"Синтез данных методом {mode}...", self, allow_cancel=True
        )

        self.worker.progress.connect(self.progress_dialog.set_progress)
        self.worker.status.connect(self.progress_dialog.set_status)
        self.worker.completed.connect(self._on_synthesis_complete)
        self.worker.error.connect(self._on_synthesis_error)
        self.worker.cancelled.connect(self._on_synthesis_cancelled)

        self.progress_dialog.set_cancel_callback(self.worker.request_cancel)
        self.synthesize_btn.setEnabled(False)
        self.worker.start()
        self.progress_dialog.exec()

    def _on_synthesis_complete(self, result):
        if not self._is_active:
            return

        self.result_df, self.result_config = result
        self.synthesize_btn.setEnabled(True)
        self.progress_dialog.accept()
        self._cleanup_worker(timeout_ms=1000)

        # Show quality report before accepting
        self._show_quality_report()

    def _show_quality_report(self):
        """Display SDV quality scores and let user confirm before saving."""
        quality = (self.result_config or {}).get("quality_evaluation")
        if not quality:
            self.accept()
            return

        overall = quality.get("overall_score", None)
        props = quality.get("properties", {})

        lines = []
        if overall is not None:
            pct = f"{overall * 100:.1f}%"
            lines.append(f"Общая оценка качества: {pct}")

        # Property scores
        prop_names = props.get("Property", {})
        prop_scores = props.get("Score", {})
        if prop_names and prop_scores:
            lines.append("")
            lines.append("Оценки свойств:")
            for idx in prop_names:
                name = prop_names[idx]
                score = prop_scores.get(idx)
                if score is not None:
                    lines.append(f"  {name}: {score * 100:.1f}%")

        lines.append("")
        lines.append("Сохранить как новую версию?")

        reply = QMessageBox.question(
            self,
            "Синтез завершён",
            "\n".join(lines),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.accept()
        else:
            # User reviewed but declined — discard result, stay open
            self.result_df = None
            self.result_config = None

    def _on_synthesis_cancelled(self):
        if not self._is_active:
            return

        self.synthesize_btn.setEnabled(True)

        if self.progress_dialog and self.progress_dialog.isVisible():
            self.progress_dialog.mark_cancelled()
            self.progress_dialog.accept()

        self._cleanup_worker(request_cancel=True, timeout_ms=1000)
        QMessageBox.information(self, "Отменено", "Операция синтеза отменена.")
        self.reject()

    def _on_synthesis_error(self, error_msg: str):
        if not self._is_active:
            return

        self.synthesize_btn.setEnabled(True)
        self.progress_dialog.accept()
        self._cleanup_worker(timeout_ms=1000)

        QMessageBox.critical(
            self,
            "Ошибка синтеза",
            f"Не удалось синтезировать данные:\n\n{error_msg}"
        )

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        self._is_active = False
        self._cleanup_worker(request_cancel=True, timeout_ms=500)
        super().closeEvent(event)

    def _cleanup_worker(self, request_cancel=False, timeout_ms=1000):
        if not hasattr(self, 'worker') or not self.worker:
            return
        try:
            if request_cancel and self.worker.isRunning():
                self.worker.request_cancel()
            self.worker.quit()
            start_time = time.time()
            timeout_s = timeout_ms / 1000.0
            while self.worker.isRunning() and time.time() - start_time < timeout_s:
                time.sleep(0.01)
            if self.worker.isRunning():
                if hasattr(self.worker, '_process') and self.worker._process:
                    if self.worker._process.is_alive():
                        self.worker._process.terminate()
                        self.worker._process.join(timeout=1)
                        if self.worker._process.is_alive():
                            self.worker._process.kill()
                            self.worker._process.join(timeout=1)
        except Exception as e:
            print(f"Ошибка очистки воркера: {e}")
