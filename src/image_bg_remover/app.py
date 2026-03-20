from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from image_bg_remover.logging_utils import configure_logging, install_exception_hook
from image_bg_remover.ui.main_window import MainWindow
from image_bg_remover.ui.theme import create_app_font


def run() -> int:
    configure_logging()

    app = QApplication(sys.argv)
    app.setApplicationName("Image BG Remover")
    app.setOrganizationName("Codex")
    app.setFont(create_app_font())

    install_exception_hook()

    logging.getLogger(__name__).info("Application starting")

    window = MainWindow()
    window.show()

    return app.exec()

