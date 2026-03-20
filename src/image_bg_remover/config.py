from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = PROJECT_ROOT / "models" / "sam2"
SUPPORTED_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")


@dataclass(frozen=True)
class ModelDefinition:
    key: str
    label: str
    checkpoint_name: str
    config_name: str

    @property
    def checkpoint_path(self) -> Path:
        return MODELS_DIR / self.checkpoint_name

    @property
    def config_path(self) -> Path:
        return MODELS_DIR / self.config_name


SUPPORTED_MODELS = (
    ModelDefinition(
        key="tiny",
        label="tiny",
        checkpoint_name="sam2.1_hiera_tiny.pt",
        config_name="sam2.1_hiera_t.yaml",
    ),
    ModelDefinition(
        key="small",
        label="small",
        checkpoint_name="sam2.1_hiera_small.pt",
        config_name="sam2.1_hiera_s.yaml",
    ),
    ModelDefinition(
        key="base_plus",
        label="base+",
        checkpoint_name="sam2.1_hiera_base_plus.pt",
        config_name="sam2.1_hiera_b+.yaml",
    ),
    ModelDefinition(
        key="large",
        label="large",
        checkpoint_name="sam2.1_hiera_large.pt",
        config_name="sam2.1_hiera_l.yaml",
    ),
)
