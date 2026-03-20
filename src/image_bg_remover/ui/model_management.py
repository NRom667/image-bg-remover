from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from image_bg_remover.config import ModelDefinition
from image_bg_remover.model_download import DownloadProgress, download_model_files
from image_bg_remover.ui.theme import dialog_stylesheet, message_box_stylesheet


class ModelDownloadWorker(QObject):
    progress = Signal(object)
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, model: ModelDefinition) -> None:
        super().__init__()
        self._model = model

    @Slot()
    def run(self) -> None:
        try:
            download_model_files(self._model, self.progress.emit)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(self._model.key)


class ModelManagementDialog(QDialog):
    def __init__(self, models: tuple[ModelDefinition, ...], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._models = models
        self._download_thread: QThread | None = None
        self._download_worker: ModelDownloadWorker | None = None
        self._active_model_key: str | None = None
        self._active_download_detail: str | None = None
        self._active_download_percent: int | None = None
        self._active_download_indeterminate = False
        self._card_widgets: dict[str, tuple[QFrame, QLabel, QLabel, QPushButton, QProgressBar]] = {}

        self.setWindowTitle("Model Management")
        self.resize(760, 460)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        description = QLabel(
            "不足しているSAM2.1モデルのcheckpoint/configをダウンロードします.",
            self,
        )
        description.setWordWrap(True)
        description.setObjectName("dialogDescriptionLabel")

        self.summary_label = QLabel(self)
        self.summary_label.setObjectName("modelSummaryLabel")

        cards_container = QWidget(self)
        cards_layout = QVBoxLayout(cards_container)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(12)

        for model in self._models:
            card = QFrame(cards_container)
            card.setObjectName("modelCard")

            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 16, 16, 16)
            card_layout.setSpacing(10)

            top_row = QHBoxLayout()
            top_row.setSpacing(12)

            text_column = QVBoxLayout()
            text_column.setSpacing(4)

            name_label = QLabel(model.label, card)
            name_label.setObjectName("modelCardTitle")

            status_label = QLabel(card)
            status_label.setObjectName("modelCardStatus")

            detail_label = QLabel(card)
            detail_label.setObjectName("modelCardDetail")
            detail_label.setWordWrap(True)

            text_column.addWidget(name_label)
            text_column.addWidget(status_label)
            text_column.addWidget(detail_label)
            top_row.addLayout(text_column, 1)

            download_button = QPushButton("ダウンロード", card)
            download_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            download_button.clicked.connect(lambda checked=False, key=model.key: self._start_download_for_model(key))
            top_row.addWidget(download_button, 0, Qt.AlignmentFlag.AlignTop)

            progress_bar = QProgressBar(card)
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            progress_bar.setVisible(False)

            card_layout.addLayout(top_row)
            card_layout.addWidget(progress_bar)

            self._card_widgets[model.key] = (card, status_label, detail_label, download_button, progress_bar)
            cards_layout.addWidget(card)

        cards_layout.addStretch(1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self.close_button = QPushButton("閉じる", self)
        self.close_button.clicked.connect(self.accept)
        button_row.addWidget(self.close_button)

        layout.addWidget(description)
        layout.addWidget(self.summary_label)
        layout.addWidget(cards_container, 1)
        layout.addLayout(button_row)

        self._refresh_cards()
        self._apply_styles()

    def _show_message_box(self, icon: QMessageBox.Icon, title: str, text: str) -> None:
        message_box = QMessageBox(self)
        message_box.setIcon(icon)
        message_box.setWindowTitle(title)
        message_box.setText(text)
        message_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        message_box.setStyleSheet(message_box_stylesheet())
        message_box.exec()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._download_thread is not None and self._download_thread.isRunning():
            self._show_message_box(QMessageBox.Icon.Information, "ダウンロード中…", "現在のダウンロードが完了するまでお待ちください")
            event.ignore()
            return
        super().closeEvent(event)

    def _start_download_for_model(self, model_key: str) -> None:
        if self._download_thread is not None and self._download_thread.isRunning():
            return

        model = next((item for item in self._models if item.key == model_key), None)
        if model is None:
            return
        if model.is_available():
            self._refresh_cards()
            return

        self._active_model_key = model.key
        self._active_download_detail = "ダウンロードを開始しています..."
        self._active_download_percent = 0
        self._active_download_indeterminate = False
        self.close_button.setEnabled(False)
        self._refresh_cards()

        self._download_thread = QThread(self)
        self._download_worker = ModelDownloadWorker(model)
        self._download_worker.moveToThread(self._download_thread)
        self._download_thread.started.connect(self._download_worker.run)
        self._download_worker.progress.connect(self._handle_progress)
        self._download_worker.finished.connect(self._handle_finished)
        self._download_worker.failed.connect(self._handle_failed)
        self._download_worker.finished.connect(self._download_thread.quit)
        self._download_worker.failed.connect(self._download_thread.quit)
        self._download_thread.finished.connect(self._cleanup_download_thread)
        self._download_thread.start()

    def _handle_progress(self, progress: DownloadProgress) -> None:
        if progress.total_bytes in (None, 0):
            size_text = self._format_bytes(progress.bytes_written)
            self._active_download_percent = None
            self._active_download_indeterminate = True
        else:
            percentage = int((progress.bytes_written / progress.total_bytes) * 100)
            self._active_download_percent = max(0, min(100, percentage))
            self._active_download_indeterminate = False
            size_text = f"{self._format_bytes(progress.bytes_written)} / {self._format_bytes(progress.total_bytes)}"

        self._active_download_detail = f"{progress.file_name} をダウンロード中 ({size_text})"
        self._refresh_cards(active_file=progress.file_name)

    def _handle_finished(self, _model_key: str) -> None:
        self.close_button.setEnabled(True)
        self._active_model_key = None
        self._active_download_detail = None
        self._active_download_percent = None
        self._active_download_indeterminate = False
        self._refresh_cards()

    def _handle_failed(self, message: str) -> None:
        self.close_button.setEnabled(True)
        self._active_model_key = None
        self._active_download_detail = None
        self._active_download_percent = None
        self._active_download_indeterminate = False
        self._refresh_cards()
        self._show_message_box(QMessageBox.Icon.Critical, "ダウンロードに失敗しました", message)

    def _cleanup_download_thread(self) -> None:
        if self._download_worker is not None:
            self._download_worker.deleteLater()
            self._download_worker = None
        if self._download_thread is not None:
            self._download_thread.deleteLater()
            self._download_thread = None

    def _refresh_cards(self, active_file: str | None = None) -> None:
        download_running = self._active_model_key is not None
        available_count = sum(1 for model in self._models if model.is_available())
        missing_count = len(self._models) - available_count

        if missing_count == 0:
            self.summary_label.setText(f"{available_count}個のモデルが利用可能です")
        elif download_running:
            self.summary_label.setText(f"{available_count} / {len(self._models)} 利用可能 | 1件ダウンロード中")
        else:
            self.summary_label.setText(f"{available_count} / {len(self._models)} 利用可能 | あと{missing_count}個ダウンロードできます")

        for model in self._models:
            card, status_label, detail_label, button, progress_bar = self._card_widgets[model.key]
            checkpoint_ready = model.checkpoint_path.exists()
            config_ready = model.config_path.exists()

            progress_bar.setVisible(False)

            if checkpoint_ready and config_ready:
                card.setProperty("cardState", "ready")
                status_label.setText("利用可能")
                detail_label.setText("checkpoint / config は配置済みです")
                button.setText("利用可能")
                button.setProperty("downloadReady", False)
                self._apply_dynamic_style(card)
                self._apply_dynamic_style(button)
                button.setEnabled(False)
                continue

            missing = []
            if not checkpoint_ready:
                missing.append(model.checkpoint_name)
            if not config_ready:
                missing.append(model.config_name)

            if self._active_model_key == model.key:
                card.setProperty("cardState", "active")
                status_label.setText("ダウンロード中")
                if self._active_download_detail is not None:
                    detail_label.setText(self._active_download_detail)
                elif active_file is not None and active_file in missing:
                    detail_label.setText(f"{active_file} をダウンロード中")
                else:
                    detail_label.setText("不足: " + ", ".join(missing))
                button.setText("ダウンロード中...")
                button.setProperty("downloadReady", False)
                self._apply_dynamic_style(card)
                self._apply_dynamic_style(button)
                button.setEnabled(False)
                progress_bar.setVisible(True)
                if self._active_download_indeterminate:
                    progress_bar.setRange(0, 0)
                else:
                    progress_bar.setRange(0, 100)
                    progress_bar.setValue(self._active_download_percent or 0)
                continue

            card.setProperty("cardState", "missing")
            status_label.setText(f"{len(missing)}ファイル不足")
            detail_label.setText("不足: " + ", ".join(missing))
            button.setText("ダウンロード")
            button.setProperty("downloadReady", not download_running)
            self._apply_dynamic_style(card)
            self._apply_dynamic_style(button)
            button.setEnabled(not download_running)

    def _format_bytes(self, size: int) -> str:
        value = float(size)
        units = ["B", "KB", "MB", "GB"]
        unit_index = 0
        while value >= 1024 and unit_index < len(units) - 1:
            value /= 1024
            unit_index += 1
        if unit_index == 0:
            return f"{int(value)} {units[unit_index]}"
        return f"{value:.1f} {units[unit_index]}"

    def _apply_dynamic_style(self, widget: QWidget) -> None:
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()

    def _apply_styles(self) -> None:
        self.setStyleSheet(dialog_stylesheet())
