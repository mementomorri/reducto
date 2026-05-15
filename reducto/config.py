"""Configuration loading."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from reducto.models import AppConfig


def load_config(config_path: str | None = None) -> AppConfig:
    cfg = AppConfig()
    paths: list[Path] = []
    if config_path:
        paths.append(Path(config_path))
    else:
        paths.extend([Path(".reducto.yaml"), Path.home() / ".reducto.yaml"])

    for p in paths:
        if p.exists():
            data = yaml.safe_load(p.read_text()) or {}
            return AppConfig.model_validate({**cfg.model_dump(), **data})
    return cfg


def apply_env(cfg: AppConfig) -> AppConfig:
    if v := os.environ.get("REDUCTO_MODEL"):
        cfg.model = v
    if os.environ.get("REDUCTO_PREFER_LOCAL", "").lower() in ("0", "false"):
        cfg.prefer_local = False
    if os.environ.get("REDUCTO_VERBOSE", "").lower() in ("1", "true"):
        cfg.verbose = True
    return cfg
