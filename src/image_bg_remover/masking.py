from __future__ import annotations

import math

import numpy as np
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


def feather_mask(mask: QImage, radius: float = 2.0) -> QImage:
    if radius <= 0:
        return mask.convertToFormat(QImage.Format.Format_Grayscale8)

    mask_gray = mask.convertToFormat(QImage.Format.Format_Grayscale8)
    mask_array = _qimage_to_numpy_gray(mask_gray).astype(np.float32)
    kernel = _build_gaussian_kernel(radius)
    blurred = _convolve_axis(_convolve_axis(mask_array, kernel, axis=1), kernel, axis=0)
    blurred = np.clip(np.rint(blurred), 0, 255).astype(np.uint8)
    return _numpy_gray_to_qimage(blurred)


def _draw_soft_circle(painter: QPainter, center: QPointF, radius: float) -> None:
    painter.drawEllipse(center, radius, radius)


def _build_gaussian_kernel(radius: float) -> np.ndarray:
    sigma = max(radius, 0.5)
    kernel_radius = max(1, int(math.ceil(sigma * 2.5)))
    offsets = np.arange(-kernel_radius, kernel_radius + 1, dtype=np.float32)
    kernel = np.exp(-(offsets**2) / (2.0 * sigma * sigma))
    kernel /= kernel.sum()
    return kernel


def _convolve_axis(array: np.ndarray, kernel: np.ndarray, axis: int) -> np.ndarray:
    pad = len(kernel) // 2
    pad_width = [(0, 0)] * array.ndim
    pad_width[axis] = (pad, pad)
    padded = np.pad(array, pad_width, mode="edge")
    return np.apply_along_axis(lambda row: np.convolve(row, kernel, mode="valid"), axis, padded)


def _qimage_to_numpy_gray(image: QImage) -> np.ndarray:
    width = image.width()
    height = image.height()
    bytes_per_line = image.bytesPerLine()
    ptr = image.constBits()
    array = np.frombuffer(ptr, dtype=np.uint8, count=bytes_per_line * height)
    return array.reshape((height, bytes_per_line))[:, :width].copy()


def _numpy_gray_to_qimage(array: np.ndarray) -> QImage:
    contiguous = np.ascontiguousarray(array)
    height, width = contiguous.shape
    return QImage(contiguous.data, width, height, width, QImage.Format.Format_Grayscale8).copy()
