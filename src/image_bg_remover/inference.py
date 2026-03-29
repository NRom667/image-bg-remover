from __future__ import annotations

from dataclasses import dataclass
import sys
from typing import Any

import numpy as np
from PySide6.QtGui import QImage

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
    def __init__(self, cache_predictors: bool | None = None, cache_models: bool = True) -> None:
        self._models: dict[str, Any] = {}
        self._predictors: dict[str, Any] = {}
        self._prepared_image_keys: dict[str, int] = {}
        self._source_image_arrays: dict[int, np.ndarray] = {}
        self._torch: Any | None = None
        self._sam2_image_predictor_cls: Any | None = None
        self._build_sam2: Any | None = None
        self._cache_predictors = (not getattr(sys, 'frozen', False)) if cache_predictors is None else cache_predictors
        self._cache_models = cache_models

    def predict_mask(
        self,
        model_key: str,
        source_image: QImage,
        foreground_points: list[PromptPoint],
        background_points: list[PromptPoint],
        soften_edges: bool = True,
        feather_radius: float = 2.0,
        source_image_key: int | None = None,
    ) -> InferenceResult:
        predictor = self._get_predictor(model_key)
        try:
            self._prepare_image(model_key, predictor, source_image, source_image_key=source_image_key)

            point_coords, point_labels = self._build_prompt_arrays(foreground_points, background_points)
            multimask_output = len(point_coords) == 1
            torch = self._get_torch_module()

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
        finally:
            if not self._cache_predictors:
                self._predictors.pop(model_key, None)
                self._prepared_image_keys.pop(model_key, None)

    def _get_predictor(self, model_key: str) -> Any:
        cached = self._predictors.get(model_key)
        if cached is not None:
            return cached

        predictor_cls = self._get_sam2_image_predictor_cls()
        model = self._get_model(model_key)
        predictor = predictor_cls(model)
        if self._cache_predictors:
            self._predictors[model_key] = predictor
        return predictor

    def _get_model(self, model_key: str) -> Any:
        cached = self._models.get(model_key)
        if cached is not None:
            return cached

        model_definition = get_model_definition(model_key)
        if model_definition is None:
            raise ValueError(f"Unknown model key: {model_key}")
        if not model_definition.checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {model_definition.checkpoint_path}")
        if not model_definition.config_path.exists():
            raise FileNotFoundError(f"Config not found: {model_definition.config_path}")

        build_sam2 = self._get_build_sam2()
        model = build_sam2(str(model_definition.config_path), str(model_definition.checkpoint_path), device="cpu")
        if self._cache_models:
            self._models[model_key] = model
        return model

    def _prepare_image(
        self,
        model_key: str,
        predictor: Any,
        source_image: QImage,
        source_image_key: int | None = None,
    ) -> None:
        image_key = int(source_image.cacheKey()) if source_image_key is None else int(source_image_key)
        if self._prepared_image_keys.get(model_key) == image_key:
            return

        image_array = self._get_source_image_array(image_key, source_image)
        predictor.set_image(image_array)
        self._prepared_image_keys[model_key] = image_key

    def _get_source_image_array(self, image_key: int, source_image: QImage) -> np.ndarray:
        cached = self._source_image_arrays.get(image_key)
        if cached is not None:
            return cached

        image_array = self._qimage_to_numpy_rgb(source_image)
        self._source_image_arrays = {image_key: image_array}
        return image_array

    def _get_torch_module(self) -> Any:
        if self._torch is None:
            import torch

            self._torch = torch
        return self._torch

    def _get_sam2_image_predictor_cls(self) -> Any:
        if self._sam2_image_predictor_cls is None:
            from sam2.sam2_image_predictor import SAM2ImagePredictor

            self._sam2_image_predictor_cls = SAM2ImagePredictor
        return self._sam2_image_predictor_cls

    def _get_build_sam2(self) -> Any:
        if self._build_sam2 is None:
            from sam2.build_sam import build_sam2

            self._build_sam2 = build_sam2
        return self._build_sam2

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
        bytes_per_line = converted.bytesPerLine()
        ptr = converted.constBits()
        array = np.frombuffer(ptr, dtype=np.uint8, count=bytes_per_line * height)
        return array.reshape((height, bytes_per_line))[:, : width * 3].reshape((height, width, 3)).copy()

    def _mask_array_to_qimage(self, mask: np.ndarray) -> QImage:
        mask_uint8 = (mask > 0).astype(np.uint8) * 255
        height, width = mask_uint8.shape
        bytes_per_line = width
        return QImage(mask_uint8.data, width, height, bytes_per_line, QImage.Format.Format_Grayscale8).copy()


