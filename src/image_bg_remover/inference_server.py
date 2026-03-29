from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage

from image_bg_remover.inference import SamInferenceEngine
from image_bg_remover.state import PromptPoint


class InferenceServer:
    def __init__(self) -> None:
        self._engine = SamInferenceEngine(cache_predictors=True, cache_models=True)
        self._cached_image_key: int | None = None
        self._cached_image_path: Path | None = None
        self._cached_image: QImage | None = None

    def run(self) -> int:
        try:
            self._engine._get_torch_module()
            self._engine._get_build_sam2()
            self._engine._get_sam2_image_predictor_cls()
        except Exception as exc:
            self._emit({"type": "fatal", "message": str(exc), "traceback": traceback.format_exc()})
            return 1

        self._emit({"type": "ready"})
        for raw_line in sys.stdin.buffer:
            line = raw_line.decode("utf-8", errors="strict").strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                self._emit({"type": "fatal", "message": "Invalid JSON request"})
                return 1

            message_type = message.get("type")
            if message_type == "shutdown":
                break
            if message_type != "predict":
                self._emit({"type": "error", "request_id": message.get("request_id"), "message": f"Unknown request type: {message_type}"})
                continue
            self._handle_predict(message)
        return 0

    def _handle_predict(self, message: dict) -> None:
        request_id = message.get("request_id")
        try:
            image_path = Path(message["image_path"])
            image_key = int(message["image_key"])
            source_image = self._load_image(image_key, image_path)
            foreground_points = [PromptPoint(float(point["x"]), float(point["y"]), "positive") for point in message.get("foreground_points", [])]
            background_points = [PromptPoint(float(point["x"]), float(point["y"]), "negative") for point in message.get("background_points", [])]
            result = self._engine.predict_mask(
                message["model_key"],
                source_image,
                foreground_points,
                background_points,
                soften_edges=bool(message.get("soften_edges", True)),
                feather_radius=float(message.get("feather_radius", 2.0)),
                source_image_key=image_key,
            )
        except Exception as exc:
            self._emit({"type": "error", "request_id": request_id, "message": str(exc), "traceback": traceback.format_exc()})
            return

        self._emit(
            {
                "type": "result",
                "request_id": request_id,
                "model_key": result.model_key,
                "score": result.score,
                "mask_png_hex": self._encode_image(result.mask),
            }
        )

    def _load_image(self, image_key: int, image_path: Path) -> QImage:
        if self._cached_image_key == image_key and self._cached_image_path == image_path and self._cached_image is not None:
            return self._cached_image

        image = QImage(str(image_path))
        if image.isNull():
            raise RuntimeError(f"画像を読み込めませんでした: {image_path}")
        self._cached_image_key = image_key
        self._cached_image_path = image_path
        self._cached_image = image
        return image

    def _encode_image(self, image: QImage) -> str:
        buffer = QBuffer()
        if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
            raise RuntimeError("PNGバッファを開けませんでした")
        if not image.save(buffer, "PNG"):
            raise RuntimeError("PNGエンコードに失敗しました")
        return bytes(buffer.data()).hex()

    def _emit(self, payload: dict) -> None:
        message = json.dumps(payload, ensure_ascii=False) + "\n"
        sys.stdout.buffer.write(message.encode("utf-8"))
        sys.stdout.buffer.flush()


def main() -> int:
    return InferenceServer().run()
