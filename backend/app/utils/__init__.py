"""Utility functions and helpers."""

import os
from typing import Dict, Any

import yaml

from .logging_config import setup_logging, get_logger
from .data_clean import clean_and_filter_dataset


def _load_model_config() -> Dict[str, Any]:
    """Load model configuration from YAML file."""
    # __file__ = .../backend/app/utils/__init__.py
    # Need to go up 2 levels to reach backend/
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    config_path = os.path.join(backend_dir, "model_config.yml")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config.get("base_models", {})
    except FileNotFoundError:
        logger = get_logger(__name__)
        logger.warning(f"Model config file not found: {config_path}, using empty config")
        return {}
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Failed to load model config: {e}")
        return {}


# Raw model config dict (key -> model_info dict)
_MODEL_CONFIG = _load_model_config()

# Legacy mapping: alias -> hf_name for backward compatibility
BASE_MODEL_MAP = {
    key: info["hf_name"]
    for key, info in _MODEL_CONFIG.items()
    if "hf_name" in info
}


def get_available_models() -> list[dict]:
    """Return list of available base models with full metadata."""
    return [
        {
            "id": key,
            "name": info.get("display_name", key),
            "type": info.get("type", ""),
            "description": info.get("description", ""),
            "params": info.get("params", ""),
            "speed": info.get("speed", ""),
            "speed_value": info.get("speed_value", 0),
        }
        for key, info in _MODEL_CONFIG.items()
    ]


__all__ = [
    "setup_logging",
    "get_logger",
    "clean_and_filter_dataset",
    "BASE_MODEL_MAP",
    "get_available_models",
]
