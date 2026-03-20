from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from image_bg_remover.config import MODELS_DIR, ModelDefinition


@dataclass(frozen=True)
class DownloadProgress:
    model_label: str
    file_name: str
    bytes_written: int
    total_bytes: int | None


def download_model_files(model: ModelDefinition, progress_callback=None) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    targets = (
        (model.config_url, model.config_path),
        (model.checkpoint_url, model.checkpoint_path),
    )
    for url, target_path in targets:
        _download_file(model.label, url, target_path, progress_callback)


def _download_file(model_label: str, url: str, target_path: Path, progress_callback) -> None:
    if target_path.exists():
        if progress_callback is not None:
            progress_callback(DownloadProgress(model_label, target_path.name, target_path.stat().st_size, target_path.stat().st_size))
        return

    temp_path = target_path.with_suffix(target_path.suffix + ".part")
    request = Request(url, headers={"User-Agent": "image-bg-remover/0.1"})
    try:
        with urlopen(request, timeout=60) as response:
            total_header = response.headers.get("Content-Length")
            total_bytes = int(total_header) if total_header is not None else None
            bytes_written = 0
            with temp_path.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
                    bytes_written += len(chunk)
                    if progress_callback is not None:
                        progress_callback(DownloadProgress(model_label, target_path.name, bytes_written, total_bytes))
        temp_path.replace(target_path)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise RuntimeError(f"{target_path.name} のダウンロードに失敗しました: {exc}") from exc
