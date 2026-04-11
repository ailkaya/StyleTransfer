"""Celery app package."""

from .tasks import celery_app, train_style_model

__all__ = ["celery_app", "train_style_model"]
