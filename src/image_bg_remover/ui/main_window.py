from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow, QSizePolicy, QVBoxLayout, QWidget

from image_bg_remover.config import MODELS_DIR, SUPPORTED_IMAGE_EXTENSIONS, SUPPORTED_MODELS


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Image BG Remover")
        self.resize(1280, 800)
        self.setMinimumSize(960, 640)

        central_widget = QWidget(self)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Image BG Remover", self)
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel(self._build_summary_text(), self)
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout.addStretch(1)
        layout.addWidget(title)
        layout.addSpacing(12)
        layout.addWidget(subtitle)
        layout.addStretch(2)

        self.setCentralWidget(central_widget)
        self._apply_styles()
        self.statusBar().showMessage("Ready")

    def _build_summary_text(self) -> str:
        model_labels = ", ".join(model.label for model in SUPPORTED_MODELS)
        image_extensions = ", ".join(SUPPORTED_IMAGE_EXTENSIONS)
        return (
            "Phase 1 scaffold is ready.\n"
            f"Models directory: {MODELS_DIR}\n"
            f"Supported models: {model_labels}\n"
            f"Supported image extensions: {image_extensions}"
        )

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f5f1e8;
            }
            QLabel#titleLabel {
                color: #1f2933;
                font-size: 28px;
                font-weight: 700;
            }
            QLabel {
                color: #334e68;
                font-size: 15px;
            }
            """
        )
