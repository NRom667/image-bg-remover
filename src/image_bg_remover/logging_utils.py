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
        _show_styled_message_box(QMessageBox.Icon.Critical, "Unexpected Error", message)

    sys.excepthook = excepthook


def _show_styled_message_box(icon: QMessageBox.Icon, title: str, text: str) -> None:
    message_box = QMessageBox()
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
