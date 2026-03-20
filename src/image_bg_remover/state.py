from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPointF
from PySide6.QtGui import QImage


@dataclass(frozen=True)
class ImageViewportMapping:
    source_width: int
    source_height: int
    display_x: float
    display_y: float
    display_width: float
    display_height: float

    def image_to_view(self, x: float, y: float) -> QPointF:
        if self.source_width == 0 or self.source_height == 0:
            return QPointF(self.display_x, self.display_y)
        return QPointF(
            self.display_x + (x / self.source_width) * self.display_width,
            self.display_y + (y / self.source_height) * self.display_height,
        )

    def view_to_image(self, x: float, y: float) -> QPointF | None:
        if self.display_width <= 0 or self.display_height <= 0:
            return None
        if not (self.display_x <= x <= self.display_x + self.display_width):
            return None
        if not (self.display_y <= y <= self.display_y + self.display_height):
            return None
        return QPointF(
            ((x - self.display_x) / self.display_width) * self.source_width,
            ((y - self.display_y) / self.display_height) * self.source_height,
        )


@dataclass
class AppState:
    image_loaded: bool = False
    mask_created: bool = False
    background_removed: bool = False
    selected_model_key: str | None = None
    image_path: Path | None = None
    source_image: QImage | None = None
    image_mapping: ImageViewportMapping | None = None

    def reset_processing(self) -> None:
        self.mask_created = False
        self.background_removed = False

    def set_image(self, image_path: Path, image: QImage) -> None:
        self.image_loaded = True
        self.image_path = image_path
        self.source_image = image
        self.image_mapping = None
        self.reset_processing()

    def clear_image(self) -> None:
        self.image_loaded = False
        self.image_path = None
        self.source_image = None
        self.image_mapping = None
        self.reset_processing()

    def full_reset(self) -> None:
        self.clear_image()
