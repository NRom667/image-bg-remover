from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal, Slot
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
    finished = Signal()
    failed = Signal(str)

    def __init__(self, models: list[ModelDefinition]) -> None:
        super().__init__()
        self._models = list(models)

    @Slot()
    def run(self) -> None:
        try:
            for model in self._models:
                download_model_files(model, self.progress.emit)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit()


class ModelManagementDialog(QDialog):
    def __init__(self, models: tuple[ModelDefinition, ...], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._models = models
        self._download_thread: QThread | None = None
        self._download_worker: ModelDownloadWorker | None = None
        self._row_widgets: dict[str, tuple[QLabel, QLabel]] = {}

        self.setWindowTitle("Model Management")
        self.resize(560, 360)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        description = QLabel(
            "Check SAM2.1 model files and download any missing checkpoint/config pair.",
            self,
        )
        description.setWordWrap(True)

        grid_frame = QFrame(self)
        grid_layout = QGridLayout(grid_frame)
        grid_layout.setContentsMargins(12, 12, 12, 12)
        grid_layout.setHorizontalSpacing(14)
        grid_layout.setVerticalSpacing(10)
        grid_layout.addWidget(QLabel("Model", grid_frame), 0, 0)
        grid_layout.addWidget(QLabel("Status", grid_frame), 0, 1)
        grid_layout.addWidget(QLabel("Details", grid_frame), 0, 2)

        for row, model in enumerate(self._models, start=1):
            name_label = QLabel(model.label, grid_frame)
            status_label = QLabel(grid_frame)
            detail_label = QLabel(grid_frame)
            detail_label.setWordWrap(True)
            self._row_widgets[model.key] = (status_label, detail_label)
            grid_layout.addWidget(name_label, row, 0)
            grid_layout.addWidget(status_label, row, 1)
            grid_layout.addWidget(detail_label, row, 2)

        self.progress_label = QLabel("Idle", self)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        button_row = QHBoxLayout()
        self.download_button = QPushButton("Download Missing Models", self)
        self.download_button.clicked.connect(self._start_download)
        self.close_button = QPushButton("Close", self)
        self.close_button.clicked.connect(self.accept)
        button_row.addWidget(self.download_button)
        button_row.addStretch(1)
        button_row.addWidget(self.close_button)

        layout.addWidget(description)
        layout.addWidget(grid_frame)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        layout.addLayout(button_row)

        self._refresh_rows()
        self._apply_styles()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._download_thread is not None and self._download_thread.isRunning():
            QMessageBox.information(self, "Download Running", "Wait for the current download to finish.")
            event.ignore()
            return
        super().closeEvent(event)

    def _start_download(self) -> None:
        missing_models = [model for model in self._models if not model.is_available()]
        if not missing_models:
            self.progress_label.setText("All model files are already available.")
            self.progress_bar.setValue(100)
            return

        self.download_button.setEnabled(False)
        self.close_button.setEnabled(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Starting download...")

        self._download_thread = QThread(self)
        self._download_worker = ModelDownloadWorker(missing_models)
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

    def _handle_finished(self) -> None:
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_label.setText("Download completed.")
        self.download_button.setEnabled(True)
        self.close_button.setEnabled(True)
        self._refresh_rows()

    def _handle_failed(self, message: str) -> None:
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Download failed.")
        self.download_button.setEnabled(True)
        self.close_button.setEnabled(True)
        self._refresh_rows()
        QMessageBox.critical(self, "Download Failed", message)

    def _cleanup_download_thread(self) -> None:
        if self._download_worker is not None:
            self._download_worker.deleteLater()
            self._download_worker = None
        if self._download_thread is not None:
            self._download_thread.deleteLater()
            self._download_thread = None

    def _refresh_rows(self, active_file: str | None = None) -> None:
        for model in self._models:
            status_label, detail_label = self._row_widgets[model.key]
            checkpoint_ready = model.checkpoint_path.exists()
            config_ready = model.config_path.exists()
            if checkpoint_ready and config_ready:
                status_label.setText("Ready")
                detail_label.setText("checkpoint / config present")
            else:
                status_label.setText("Missing")
                missing = []
                if not checkpoint_ready:
                    missing.append(model.checkpoint_name)
                if not config_ready:
                    missing.append(model.config_name)
                if active_file is not None and active_file in missing:
                    detail_label.setText(f"downloading: {active_file}")
                else:
                    detail_label.setText("missing: " + ", ".join(missing))

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
