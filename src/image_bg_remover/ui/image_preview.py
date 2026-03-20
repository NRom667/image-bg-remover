from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from image_bg_remover.state import ImageViewportMapping, PromptPoint


class ImagePreviewWidget(QWidget):
    mapping_changed = Signal(object)
    interaction_requested = Signal(object, float, float, float)

    def __init__(self, placeholder_text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._placeholder_text = placeholder_text
        self._image: QImage | None = None
        self._pixmap: QPixmap | None = None
        self._mask_overlay: QImage | None = None
        self._mask_overlay_pixmap: QPixmap | None = None
        self._mapping: ImageViewportMapping | None = None
        self._foreground_points: list[PromptPoint] = []
        self._background_points: list[PromptPoint] = []
        self.setMinimumHeight(280)
        self.setMouseTracking(True)

    def set_image(self, image: QImage | None) -> None:
        self._image = image
        self._pixmap = QPixmap.fromImage(image) if image is not None else None
        self._update_layout_cache()
        self.update()

    def set_mask_overlay(self, overlay: QImage | None) -> None:
        self._mask_overlay = overlay
        self._mask_overlay_pixmap = QPixmap.fromImage(overlay) if overlay is not None else None
        self.update()

    def set_points(self, foreground_points: list[PromptPoint], background_points: list[PromptPoint]) -> None:
        self._foreground_points = list(foreground_points)
        self._background_points = list(background_points)
        self.update()

    def current_mapping(self) -> ImageViewportMapping | None:
        return self._mapping

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_layout_cache()
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._mapping is None:
            super().mousePressEvent(event)
            return

        image_point = self._mapping.view_to_image(event.position().x(), event.position().y())
        if image_point is None:
            super().mousePressEvent(event)
            return

        scale = max(self._mapping.pixels_per_image_unit(), 1e-6)
        delete_threshold = 18.0 / scale
        self.interaction_requested.emit(event.button(), image_point.x(), image_point.y(), delete_threshold)
        event.accept()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            rect = self.rect().adjusted(1, 1, -1, -1)
            painter.fillRect(rect, QColor("#fffdf8"))
            painter.setPen(QColor("#d9cdbb"))
            painter.drawRoundedRect(rect, 18, 18)

            body_rect = QRectF(rect.adjusted(18, 18, -18, -18))
            self._draw_checker_background(painter, body_rect)

            if self._pixmap is None or self._mapping is None:
                painter.setPen(QColor("#7b8794"))
                placeholder_font = QFont(self.font())
                placeholder_font.setPointSize(16)
                painter.setFont(placeholder_font)
                painter.drawText(body_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self._placeholder_text)
                return

            target_rect = QRectF(
                self._mapping.display_x,
                self._mapping.display_y,
                self._mapping.display_width,
                self._mapping.display_height,
            )
            painter.drawPixmap(target_rect, self._pixmap, QRectF(self._pixmap.rect()))
            if self._mask_overlay_pixmap is not None:
                painter.drawPixmap(target_rect, self._mask_overlay_pixmap, QRectF(self._mask_overlay_pixmap.rect()))
            self._draw_points(painter)
        finally:
            if painter.isActive():
                painter.end()

    def _draw_points(self, painter: QPainter) -> None:
        if self._mapping is None:
            return
        for point in self._foreground_points:
            self._draw_point_marker(painter, point, QColor("#d64545"), "+")
        for point in self._background_points:
            self._draw_point_marker(painter, point, QColor("#2b6cb0"), "-")

    def _draw_point_marker(self, painter: QPainter, point: PromptPoint, color: QColor, symbol: str) -> None:
        if self._mapping is None:
            return

        center = self._mapping.image_to_view(point.x, point.y)
        marker_radius = 11.0
        glyph_radius = 5.0

        painter.save()
        painter.setBrush(color)
        painter.setPen(QPen(QColor("#ffffff"), 1.5))
        painter.drawEllipse(center, marker_radius, marker_radius)

        glyph_pen = QPen(QColor("#ffffff"), 2.2)
        glyph_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(glyph_pen)
        painter.drawLine(
            int(round(center.x() - glyph_radius)),
            int(round(center.y())),
            int(round(center.x() + glyph_radius)),
            int(round(center.y())),
        )
        if symbol == "+":
            painter.drawLine(
                int(round(center.x())),
                int(round(center.y() - glyph_radius)),
                int(round(center.x())),
                int(round(center.y() + glyph_radius)),
            )
        painter.restore()

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
