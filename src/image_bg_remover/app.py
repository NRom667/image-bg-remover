from __future__ import annotations

import ctypes
import logging
import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from image_bg_remover.logging_utils import configure_logging, install_exception_hook
from image_bg_remover.paths import get_image_asset_path
from image_bg_remover.ui.theme import create_app_font

WINDOWS_APP_ID = "Rom.BGRemover"


def _preload_inference_runtime() -> None:
    from image_bg_remover.inference import SamInferenceEngine

    engine = SamInferenceEngine()
    engine._get_torch_module()
    engine._get_build_sam2()
    engine._get_sam2_image_predictor_cls()


def _configure_windows_app_id() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
    except (AttributeError, OSError):
        logging.getLogger(__name__).debug("Failed to set Windows AppUserModelID", exc_info=True)


def run() -> int:
    from image_bg_remover.ui.main_window import MainWindow

    configure_logging()
    _configure_windows_app_id()

    app = QApplication(sys.argv)
    app.setApplicationName("BG Remover")
    app.setOrganizationName("Rom")
    app.setFont(create_app_font())
    app_icon = QIcon(str(get_image_asset_path("icon.ico")))
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    install_exception_hook()

    logging.getLogger(__name__).info("Application starting")

    window = MainWindow()
    if not app_icon.isNull():
        window.setWindowIcon(app_icon)
    window.showMaximized()
    QTimer.singleShot(0, _preload_inference_runtime)

    return app.exec()
