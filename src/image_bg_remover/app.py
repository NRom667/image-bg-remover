from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from image_bg_remover.logging_utils import configure_logging, install_exception_hook
from image_bg_remover.ui.main_window import MainWindow


def run() -> int:
    configure_logging()

    app = QApplication(sys.argv)
    app.setApplicationName("Image BG Remover")
    app.setOrganizationName("Codex")

    install_exception_hook()

    logging.getLogger(__name__).info("Application starting")

    window = MainWindow()
    window.show()

    return app.exec()
