from __future__ import annotations

import logging
import sys
import traceback

from PySide6.QtWidgets import QMessageBox


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def install_exception_hook() -> None:
    def excepthook(exc_type: type[BaseException], exc_value: BaseException, exc_traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger = logging.getLogger("image_bg_remover")
        logger.exception("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))

        message = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        QMessageBox.critical(None, "Unexpected Error", message)

    sys.excepthook = excepthook
