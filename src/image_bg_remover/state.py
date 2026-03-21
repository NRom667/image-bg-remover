from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QPointF
from PySide6.QtGui import QImage


@dataclass(frozen=True)
class PromptPoint:
    x: float
    y: float
    kind: str


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

    def pixels_per_image_unit(self) -> float:
        if self.source_width <= 0 or self.source_height <= 0:
            return 1.0
        return min(self.display_width / self.source_width, self.display_height / self.source_height)


@dataclass
class AppState:
    image_loaded: bool = False
    mask_created: bool = False
    background_removed: bool = False
    selected_model_key: str | None = None
    image_path: Path | None = None
    source_image: QImage | None = None
    image_mapping: ImageViewportMapping | None = None
    foreground_points: list[PromptPoint] = field(default_factory=list)
    background_points: list[PromptPoint] = field(default_factory=list)
    current_mask: QImage | None = None
    mask_overlay: QImage | None = None
    background_removed_image: QImage | None = None

    def reset_processing(self) -> None:
        self.mask_created = False
        self.background_removed = False
        self.current_mask = None
        self.mask_overlay = None
        self.background_removed_image = None

    def set_image(self, image_path: Path, image: QImage) -> None:
        self.image_loaded = True
        self.image_path = image_path
        self.source_image = image
        self.image_mapping = None
        self.foreground_points.clear()
        self.background_points.clear()
        self.reset_processing()

    def add_point(self, x: float, y: float, kind: str) -> None:
        point = PromptPoint(x=x, y=y, kind=kind)
        if kind == "positive":
            self.foreground_points.append(point)
        else:
            self.background_points.append(point)

    def remove_nearest_point(self, x: float, y: float, max_distance: float) -> PromptPoint | None:
        nearest: tuple[str, int, float] | None = None
        for kind, points in (("positive", self.foreground_points), ("negative", self.background_points)):
            for index, point in enumerate(points):
                distance_sq = (point.x - x) ** 2 + (point.y - y) ** 2
                if nearest is None or distance_sq < nearest[2]:
                    nearest = (kind, index, distance_sq)

        if nearest is None or nearest[2] > max_distance**2:
            return None

        kind, index, _ = nearest
        if kind == "positive":
            return self.foreground_points.pop(index)
        return self.background_points.pop(index)

    def set_mask(self, mask: QImage, overlay: QImage) -> None:
        self.current_mask = mask
        self.mask_overlay = overlay
        self.mask_created = True
        self.background_removed = False
        self.background_removed_image = None

    def set_background_removed_image(self, image: QImage) -> None:
        self.background_removed_image = image
        self.background_removed = True

    def clear_points(self) -> None:
        self.foreground_points.clear()
        self.background_points.clear()
        self.reset_processing()

    def clear_image(self) -> None:
        self.image_loaded = False
        self.image_path = None
        self.source_image = None
        self.image_mapping = None
        self.clear_points()

    def full_reset(self) -> None:
        self.clear_image()
