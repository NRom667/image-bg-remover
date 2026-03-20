from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from image_bg_remover.config import ModelDefinition
from image_bg_remover.model_download import DownloadProgress, download_model_files


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
        self._row_widgets: dict[str, tuple[QPushButton, QLabel, QLabel]] = {}

        self.setWindowTitle("Model Management")
        self.resize(720, 360)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        description = QLabel(
            "Download a checkpoint/config pair for any missing SAM2.1 model.",
            self,
        )
        description.setWordWrap(True)

        grid_frame = QFrame(self)
        grid_layout = QGridLayout(grid_frame)
        grid_layout.setContentsMargins(12, 12, 12, 12)
        grid_layout.setHorizontalSpacing(14)
        grid_layout.setVerticalSpacing(10)
        for column, title in enumerate(("Download", "Model", "Status", "Details")):
            header_label = QLabel(title, grid_frame)
            header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid_layout.addWidget(header_label, 0, column)

        for row, model in enumerate(self._models, start=1):
            download_button = QPushButton("Download", grid_frame)
            download_button.clicked.connect(lambda checked=False, key=model.key: self._start_download_for_model(key))
            name_label = QLabel(model.label, grid_frame)
            name_label.setMargin(8)
            status_label = QLabel(grid_frame)
            status_label.setMargin(8)
            detail_label = QLabel(grid_frame)
            detail_label.setMargin(8)
            detail_label.setWordWrap(True)
            self._row_widgets[model.key] = (download_button, status_label, detail_label)
            grid_layout.addWidget(download_button, row, 0)
            grid_layout.addWidget(name_label, row, 1)
            grid_layout.addWidget(status_label, row, 2)
            grid_layout.addWidget(detail_label, row, 3)

        self.progress_label = QLabel("Idle", self)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self.close_button = QPushButton("Close", self)
        self.close_button.clicked.connect(self.accept)
        button_row.addWidget(self.close_button)

        layout.addWidget(description)
        layout.addWidget(grid_frame)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        layout.addLayout(button_row)

        self._refresh_rows()
        self._apply_styles()

    def _show_message_box(self, icon: QMessageBox.Icon, title: str, text: str) -> None:
        message_box = QMessageBox(self)
        message_box.setIcon(icon)
        message_box.setWindowTitle(title)
        message_box.setText(text)
        message_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        message_box.setStyleSheet(
            """
            QMessageBox {
                background: #f8f3ea;
            }
            QMessageBox QLabel {
                color: #102a43;
                font-size: 14px;
            }
            QMessageBox QPushButton {
                min-width: 88px;
                min-height: 38px;
                border-radius: 12px;
                border: 1px solid #d9cdbb;
                padding: 8px 16px;
                background: #fffdf8;
                color: #102a43;
                font-size: 14px;
            }
            QMessageBox QPushButton:hover {
                border: 1px solid #bfa98a;
                background: #fff6e8;
            }
            """
        )
        message_box.exec()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._download_thread is not None and self._download_thread.isRunning():
            self._show_message_box(QMessageBox.Icon.Information, "Download Running", "Wait for the current download to finish.")
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
            self.progress_label.setText(f"{model.label}: already available")
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
            self._refresh_rows()
            return

        self._active_model_key = model.key
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"{model.label}: starting download...")
        self.close_button.setEnabled(False)
        self._refresh_rows()

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
            self.progress_bar.setRange(0, 0)
            size_text = self._format_bytes(progress.bytes_written)
        else:
            self.progress_bar.setRange(0, 100)
            percentage = int((progress.bytes_written / progress.total_bytes) * 100)
            self.progress_bar.setValue(max(0, min(100, percentage)))
            size_text = f"{self._format_bytes(progress.bytes_written)} / {self._format_bytes(progress.total_bytes)}"

        self.progress_label.setText(f"{progress.model_label}: downloading {progress.file_name} ({size_text})")
        self._refresh_rows(active_file=progress.file_name)

    def _handle_finished(self, model_key: str) -> None:
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        model = next((item for item in self._models if item.key == model_key), None)
        label = model.label if model is not None else model_key
        self.progress_label.setText(f"{label}: download completed")
        self.close_button.setEnabled(True)
        self._active_model_key = None
        self._refresh_rows()

    def _handle_failed(self, message: str) -> None:
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Download failed.")
        self.close_button.setEnabled(True)
        self._active_model_key = None
        self._refresh_rows()
        self._show_message_box(QMessageBox.Icon.Critical, "Download Failed", message)

    def _cleanup_download_thread(self) -> None:
        if self._download_worker is not None:
            self._download_worker.deleteLater()
            self._download_worker = None
        if self._download_thread is not None:
            self._download_thread.deleteLater()
            self._download_thread = None

    def _refresh_rows(self, active_file: str | None = None) -> None:
        download_running = self._active_model_key is not None
        for model in self._models:
            button, status_label, detail_label = self._row_widgets[model.key]
            checkpoint_ready = model.checkpoint_path.exists()
            config_ready = model.config_path.exists()

            if checkpoint_ready and config_ready:
                status_label.setText("Ready")
                detail_label.setText("checkpoint / config present")
                button.setText("Ready")
                button.setEnabled(False)
                continue

            missing = []
            if not checkpoint_ready:
                missing.append(model.checkpoint_name)
            if not config_ready:
                missing.append(model.config_name)

            if self._active_model_key == model.key:
                status_label.setText("Downloading")
                button.setText("Downloading...")
                button.setEnabled(False)
                if active_file is not None and active_file in missing:
                    detail_label.setText(f"downloading: {active_file}")
                else:
                    detail_label.setText("missing: " + ", ".join(missing))
                continue

            status_label.setText("Missing")
            detail_label.setText("missing: " + ", ".join(missing))
            button.setText("Download")
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

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QDialog {
                background: #f8f3ea;
            }
            QFrame {
                background: #fffdf9;
                border: 1px solid #e6dccb;
                border-radius: 16px;
            }
            QLabel {
                color: #334e68;
                font-size: 13px;
            }
            QPushButton {
                min-height: 40px;
                border-radius: 12px;
                border: 1px solid #d9cdbb;
                padding: 8px 12px;
                background: #fffdf8;
                color: #102a43;
                font-size: 14px;
            }
            QPushButton:hover {
                border: 1px solid #bfa98a;
                background: #fff6e8;
            }
            QPushButton:disabled {
                color: #9aa5b1;
                background: #f4efe6;
                border: 1px solid #e0d7ca;
            }
            QProgressBar {
                min-height: 24px;
                border: 1px solid #d9cdbb;
                border-radius: 10px;
                background: #fffdf8;
                text-align: center;
                color: #243b53;
            }
            QProgressBar::chunk {
                border-radius: 9px;
                background: #c17c3c;
            }
            """
        )
