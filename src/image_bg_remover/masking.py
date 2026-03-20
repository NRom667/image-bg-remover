from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QImage, QPainter

from image_bg_remover.state import PromptPoint


def build_dummy_mask(source_image: QImage, foreground_points: list[PromptPoint], background_points: list[PromptPoint]) -> QImage:
    mask = QImage(source_image.size(), QImage.Format.Format_Grayscale8)
    mask.fill(0)

    painter = QPainter(mask)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        positive_radius = max(20.0, min(source_image.width(), source_image.height()) * 0.08)
        negative_radius = positive_radius * 0.9

        painter.setBrush(QColor(255, 255, 255))
        for point in foreground_points:
            _draw_soft_circle(painter, QPointF(point.x, point.y), positive_radius)

        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        for point in background_points:
            _draw_soft_circle(painter, QPointF(point.x, point.y), negative_radius)
    finally:
        if painter.isActive():
            painter.end()

    return mask


def build_mask_overlay(mask: QImage) -> QImage:
    overlay = QImage(mask.size(), QImage.Format.Format_ARGB32_Premultiplied)
    overlay.fill(Qt.GlobalColor.transparent)

    for y in range(mask.height()):
        for x in range(mask.width()):
            alpha = mask.pixelColor(x, y).red()
            if alpha == 0:
                continue
            overlay.setPixelColor(x, y, QColor(220, 69, 69, min(150, alpha)))

    return overlay


def apply_mask_to_image(source_image: QImage, mask: QImage) -> QImage:
    result = source_image.convertToFormat(QImage.Format.Format_ARGB32)
    mask_gray = mask.convertToFormat(QImage.Format.Format_Grayscale8)

    for y in range(result.height()):
        for x in range(result.width()):
            color = result.pixelColor(x, y)
            color.setAlpha(mask_gray.pixelColor(x, y).red())
            result.setPixelColor(x, y, color)

    return result


def _draw_soft_circle(painter: QPainter, center: QPointF, radius: float) -> None:
    painter.drawEllipse(center, radius, radius)
