from __future__ import annotations

import logging
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from image_bg_remover.logging_utils import configure_logging, install_exception_hook
from image_bg_remover.ui.main_window import MainWindow
from image_bg_remover.ui.theme import create_app_font


def _preload_inference_runtime() -> None:
    from image_bg_remover.inference import SamInferenceEngine

    engine = SamInferenceEngine()
    engine._get_torch_module()
    engine._get_build_sam2()
    engine._get_sam2_image_predictor_cls()


def run() -> int:
    configure_logging()

    app = QApplication(sys.argv)
    app.setApplicationName("Image BG Remover")
    app.setOrganizationName("Codex")
    app.setFont(create_app_font())

    install_exception_hook()

    logging.getLogger(__name__).info("Application starting")

    window = MainWindow()
    window.showMaximized()
    QTimer.singleShot(0, _preload_inference_runtime)

    return app.exec()
