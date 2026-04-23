"""Application configuration."""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings


def parse_cors_origins(value: str) -> List[str]:
    """Parse CORS origins from string to list."""
    if not value or value.strip() == "":
        return ["*"]
    return [origin.strip() for origin in value.split(",")]


class Settings(BaseSettings):
    """Application settings."""

    # App
    APP_NAME: str = "Style Transfer API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/style_transfer"
    SYNC_DATABASE_URL: Optional[str] = "postgresql://postgres:postgres@127.0.0.1:5432/style_transfer"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None

    # LLM API (OpenAI compatible)
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL_NAME: str = "gpt-3.5-turbo"
    LLM_API_KEY: Optional[str] = None
    LLM_TIMEOUT: int = 60

    # File storage
    UPLOAD_DIR: str = "./uploads"
    MODELS_DIR: str = "./models"
    MAX_UPLOAD_SIZE: int = 10

    # CORS - comma-separated string like "http://localhost:3000,http://localhost:8080"
    CORS_ORIGINS: str = "*"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None

    GENERATING_MOCK_MODE: bool = True

    # Evaluation
    EVALUATION_SAMPLE_COUNT: int = 5
    EVALUATION_MOCK_DELAY: int = 20
    EVALUATION_MOCK_MODE: bool = True
    APPLY_COMMENT_ADJUSTMENT: bool = False

    # Training
    TRAINING_MOCK_MODE: bool = True
    TRAINING_USE_CHUNK_DATA: bool = True

    # Task Recovery
    RECOVER_PENDING_TASKS_ON_STARTUP: bool = True

    ENABLE_MESSAGE_HISTORY: bool = True

    # Model Manager - GPU memory reservation ratio (0.15 ~ 0.20)
    MODEL_RESERVED_GPU_RATIO: float = 0.18

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Allow extra fields from env file
        extra = "ignore"

    def get_cors_origins(self) -> List[str]:
        """Get CORS origins as a list."""
        return parse_cors_origins(self.CORS_ORIGINS)


settings = Settings()
