from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from image_bg_remover.state import ImageViewportMapping


class ImagePreviewWidget(QWidget):
    mapping_changed = Signal(object)

    def __init__(self, placeholder_text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._placeholder_text = placeholder_text
        self._image: QImage | None = None
        self._pixmap: QPixmap | None = None
        self._mapping: ImageViewportMapping | None = None
        self.setMinimumHeight(280)

    def set_image(self, image: QImage | None) -> None:
        self._image = image
        self._pixmap = QPixmap.fromImage(image) if image is not None else None
        self._update_layout_cache()
        self.update()

    def current_mapping(self) -> ImageViewportMapping | None:
        return self._mapping

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_layout_cache()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.fillRect(rect, QColor("#fffdf8"))
        painter.setPen(QColor("#d9cdbb"))
        painter.drawRoundedRect(rect, 18, 18)

        body_rect = QRectF(rect.adjusted(18, 18, -18, -18))
        self._draw_checker_background(painter, body_rect)

        if self._pixmap is None or self._mapping is None:
            painter.setPen(QColor("#7b8794"))
            painter.drawText(body_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self._placeholder_text)
            painter.end()
            return

        target_rect = QRectF(
            self._mapping.display_x,
            self._mapping.display_y,
            self._mapping.display_width,
            self._mapping.display_height,
        )
        painter.drawPixmap(target_rect, self._pixmap, QRectF(self._pixmap.rect()))
        painter.end()

    def _update_layout_cache(self) -> None:
        if self._image is None or self._image.isNull():
            self._mapping = None
            self.mapping_changed.emit(None)
            return

        available = self.rect().adjusted(19, 19, -19, -19)
        if available.width() <= 0 or available.height() <= 0:
            self._mapping = None
            self.mapping_changed.emit(None)
            return

        source_width = self._image.width()
        source_height = self._image.height()
        scale = min(available.width() / source_width, available.height() / source_height)
        display_width = source_width * scale
        display_height = source_height * scale
        display_x = available.x() + (available.width() - display_width) / 2
        display_y = available.y() + (available.height() - display_height) / 2

        mapping = ImageViewportMapping(
            source_width=source_width,
            source_height=source_height,
            display_x=display_x,
            display_y=display_y,
            display_width=display_width,
            display_height=display_height,
        )

        if mapping != self._mapping:
            self._mapping = mapping
            self.mapping_changed.emit(mapping)

    def _draw_checker_background(self, painter: QPainter, rect: QRectF) -> None:
        tile = 18
        light = QColor("#fbf7ef")
        dark = QColor("#f0e7d8")
        y = rect.top()
        row = 0
        while y < rect.bottom():
            x = rect.left()
            col = row
            while x < rect.right():
                color = light if col % 2 == 0 else dark
                painter.fillRect(QRectF(x, y, tile, tile), color)
                x += tile
                col += 1
            y += tile
            row += 1
