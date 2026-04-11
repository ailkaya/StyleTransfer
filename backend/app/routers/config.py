"""API routes for system configuration."""

import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models import get_db, Config
from ..schemas import Response, LLMConfig, LLMConfigResponse
from ..services import inference_service

router = APIRouter(prefix="/api/config", tags=["config"])

# Config keys
LLM_BASE_URL_KEY = "llm_base_url"
LLM_MODEL_NAME_KEY = "llm_model_name"
LLM_API_KEY_KEY = "llm_api_key"


@router.get("/llm", response_model=Response)
async def get_llm_config(
    db: AsyncSession = Depends(get_db),
):
    """Get LLM configuration (without API key)."""
    # Try to get from database first
    base_url_result = await db.execute(
        select(Config).where(Config.key == LLM_BASE_URL_KEY)
    )
    base_url_config = base_url_result.scalar_one_or_none()

    model_name_result = await db.execute(
        select(Config).where(Config.key == LLM_MODEL_NAME_KEY)
    )
    model_name_config = model_name_result.scalar_one_or_none()

    api_key_result = await db.execute(
        select(Config).where(Config.key == LLM_API_KEY_KEY)
    )
    api_key_config = api_key_result.scalar_one_or_none()

    # Fallback to environment variables
    base_url = (base_url_config.value if base_url_config
                else os.getenv("LLM_BASE_URL", ""))
    model_name = (model_name_config.value if model_name_config
                  else os.getenv("LLM_MODEL_NAME", ""))
    has_api_key = bool(api_key_config) or bool(os.getenv("LLM_API_KEY"))

    return Response(
        code=200,
        message="success",
        data=LLMConfigResponse(
            base_url=base_url,
            model_name=model_name,
            has_api_key=has_api_key,
        ),
        timestamp=datetime.utcnow(),
    )


@router.put("/llm", response_model=Response)
async def update_llm_config(
    config_data: LLMConfig,
    db: AsyncSession = Depends(get_db),
):
    """Update LLM configuration."""
    # Update or create each config entry
    configs_to_update = [
        (LLM_BASE_URL_KEY, config_data.base_url, "LLM API base URL"),
        (LLM_MODEL_NAME_KEY, config_data.model_name, "LLM model name"),
        (LLM_API_KEY_KEY, config_data.api_key, "LLM API key"),
    ]

    for key, value, description in configs_to_update:
        result = await db.execute(
            select(Config).where(Config.key == key)
        )
        config = result.scalar_one_or_none()

        if config:
            config.value = value
            config.updated_at = datetime.utcnow()
        else:
            new_config = Config(
                key=key,
                value=value,
                description=description,
            )
            db.add(new_config)

    await db.commit()

    # Update inference service
    await inference_service.update_config(
        base_url=config_data.base_url,
        model_name=config_data.model_name,
        api_key=config_data.api_key,
    )

    # Verify connection
    is_valid = await inference_service.verify_connection()

    return Response(
        code=200,
        message="LLM configuration updated successfully" if is_valid
                else "Configuration saved but connection test failed",
        data=LLMConfigResponse(
            base_url=config_data.base_url,
            model_name=config_data.model_name,
            has_api_key=bool(config_data.api_key),
        ),
        timestamp=datetime.utcnow(),
    )


@router.post("/llm/verify", response_model=Response)
async def verify_llm_config(
    db: AsyncSession = Depends(get_db),
):
    """Verify LLM API connection."""
    is_valid = await inference_service.verify_connection()

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM API connection failed. Please check your configuration."
        )

    return Response(
        code=200,
        message="LLM API connection verified successfully",
        data={"connected": True},
        timestamp=datetime.utcnow(),
    )
