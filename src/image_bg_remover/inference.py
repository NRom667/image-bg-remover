from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from PySide6.QtGui import QImage
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor

from image_bg_remover.config import get_model_definition
from image_bg_remover.masking import build_mask_overlay, feather_mask
from image_bg_remover.state import PromptPoint


@dataclass
class InferenceResult:
    mask: QImage
    overlay: QImage
    score: float
    model_key: str


class SamInferenceEngine:
    def __init__(self) -> None:
        self._predictors: dict[str, SAM2ImagePredictor] = {}

    def predict_mask(
        self,
        model_key: str,
        source_image: QImage,
        foreground_points: list[PromptPoint],
        background_points: list[PromptPoint],
        soften_edges: bool = True,
        feather_radius: float = 2.0,
    ) -> InferenceResult:
        predictor = self._get_predictor(model_key)
        image_array = self._qimage_to_numpy_rgb(source_image)
        predictor.set_image(image_array)

        point_coords, point_labels = self._build_prompt_arrays(foreground_points, background_points)
        multimask_output = len(point_coords) == 1

        with torch.inference_mode():
            masks, scores, _ = predictor.predict(
                point_coords=point_coords,
                point_labels=point_labels,
                multimask_output=multimask_output,
            )

        best_index = int(np.argmax(scores))
        best_mask = masks[best_index]
        mask_image = self._mask_array_to_qimage(best_mask)
        if soften_edges:
            mask_image = feather_mask(mask_image, radius=feather_radius)
        overlay = build_mask_overlay(mask_image)
        return InferenceResult(mask=mask_image, overlay=overlay, score=float(scores[best_index]), model_key=model_key)

    def _get_predictor(self, model_key: str) -> SAM2ImagePredictor:
        cached = self._predictors.get(model_key)
        if cached is not None:
            return cached

        model_definition = get_model_definition(model_key)
        if model_definition is None:
            raise ValueError(f"Unknown model key: {model_key}")
        if not model_definition.checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {model_definition.checkpoint_path}")
        if not model_definition.config_path.exists():
            raise FileNotFoundError(f"Config not found: {model_definition.config_path}")

        model = build_sam2(str(model_definition.config_path), str(model_definition.checkpoint_path), device="cpu")
        predictor = SAM2ImagePredictor(model)
        self._predictors[model_key] = predictor
        return predictor

    def _build_prompt_arrays(self, foreground_points: list[PromptPoint], background_points: list[PromptPoint]) -> tuple[np.ndarray, np.ndarray]:
        prompt_points = [*foreground_points, *background_points]
        if not prompt_points:
            raise ValueError("At least one prompt point is required")

        point_coords = np.array([[point.x, point.y] for point in prompt_points], dtype=np.float32)
        point_labels = np.array([1 if point.kind == "positive" else 0 for point in prompt_points], dtype=np.int32)
        return point_coords, point_labels

    def _qimage_to_numpy_rgb(self, image: QImage) -> np.ndarray:
        converted = image.convertToFormat(QImage.Format.Format_RGB888)
        width = converted.width()
        height = converted.height()
        ptr = converted.constBits()
        return np.frombuffer(ptr, dtype=np.uint8).reshape((height, width, 3)).copy()

    def _mask_array_to_qimage(self, mask: np.ndarray) -> QImage:
        mask_uint8 = (mask > 0).astype(np.uint8) * 255
        height, width = mask_uint8.shape
        bytes_per_line = width
        return QImage(mask_uint8.data, width, height, bytes_per_line, QImage.Format.Format_Grayscale8).copy()
