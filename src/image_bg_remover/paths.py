from __future__ import annotations

import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parents[1]


def get_app_root() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return PROJECT_ROOT


def get_bundle_root() -> Path | None:
    if getattr(sys, 'frozen', False):
        bundle_root = getattr(sys, '_MEIPASS', None)
        if bundle_root:
            return Path(bundle_root)
    return None


def get_models_dir() -> Path:
    runtime_models_dir = get_app_root() / 'models' / 'sam2'
    if not getattr(sys, 'frozen', False):
        return runtime_models_dir

    if runtime_models_dir.exists():
        return runtime_models_dir

    bundle_root = get_bundle_root()
    if bundle_root is not None:
        bundled_models_dir = bundle_root / 'models' / 'sam2'
        if bundled_models_dir.exists():
            return bundled_models_dir

    return runtime_models_dir
