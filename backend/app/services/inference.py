"""Inference service for style transfer using external LLM API."""

import os
from typing import List, Optional
import httpx
from openai import AsyncOpenAI

from ..schemas import ChatMessage
from ..utils import get_logger

logger = get_logger(__name__)


class InferenceService:
    """Service for calling external LLM API for style transfer."""

    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self.model_name: str = "gpt-3.5-turbo"
        self._init_client()

    def _init_client(self):
        """Initialize OpenAI client from config."""
        from config import settings

        logger.debug(f"Initializing inference client: base_url={settings.LLM_BASE_URL}, has_key={settings.LLM_API_KEY is not None}")

        if settings.LLM_API_KEY:
            self.client = AsyncOpenAI(
                base_url=settings.LLM_BASE_URL,
                api_key=settings.LLM_API_KEY,
                timeout=settings.LLM_TIMEOUT,
            )
            self.model_name = settings.LLM_MODEL_NAME
            logger.info(f"Inference client initialized: {settings.LLM_BASE_URL}, model={settings.LLM_MODEL_NAME}")
        else:
            logger.warning("LLM_API_KEY not set, inference client not initialized")

    async def update_config(self, base_url: str, model_name: str, api_key: str):
        """Update LLM configuration."""
        self.model_name = model_name
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
        )

    def _build_prompt(
        self,
        original_text: str,
        requirement: str,
        target_style: str,
    ) -> str:
        """Build the prompt for style transfer."""
        prompt = f"""请将以下文本转换为"{target_style}"风格。

转换要求：{requirement}

原文：
{original_text}

请直接输出转换后的文本，不要添加任何解释说明。"""
        return prompt

    def _ensure_configured(self):
        """Ensure client is configured, retry once if not."""
        if self.client is None:
            # Try to reload config
            from config import settings
            if settings.LLM_API_KEY:
                self.client = AsyncOpenAI(
                    base_url=settings.LLM_BASE_URL,
                    api_key=settings.LLM_API_KEY,
                    timeout=settings.LLM_TIMEOUT,
                )
                self.model_name = settings.LLM_MODEL_NAME
                logger.info(f"Inference service configured on-demand: {settings.LLM_BASE_URL}")

    async def generate_style_transfer(
        self,
        original_text: str,
        requirement: str,
        target_style: str,
        history: Optional[List[ChatMessage]] = None,
    ) -> str:
        """
        Generate style-transferred text using external LLM API.

        Args:
            original_text: Original text to transform
            requirement: Specific transformation requirements
            target_style: Target style name
            history: Optional chat history for context

        Returns:
            Transformed text

        Raises:
            ValueError: If LLM client is not configured
            RuntimeError: If API call fails
        """
        # Try to configure on-demand if not already done
        self._ensure_configured()

        if not self.client:
            raise ValueError(
                "LLM client not configured. Please set LLM_BASE_URL, "
                "LLM_API_KEY, and LLM_MODEL_NAME environment variables."
            )

        messages = []

        # Add system message
        messages.append({
            "role": "system",
            "content": f"你是一个专业的文本风格转换助手。你的任务是将用户提供的文本转换为'{target_style}'风格，同时保持原文的核心含义。"
        })

        # Add history if provided
        if history:
            for msg in history:
                messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })

        # Add user prompt
        prompt = self._build_prompt(original_text, requirement, target_style)
        messages.append({
            "role": "user",
            "content": prompt,
        })

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=2048,
                timeout=30.0,
            )

            return response.choices[0].message.content

        except httpx.TimeoutException:
            raise RuntimeError("LLM API call timed out after 30 seconds")
        except Exception as e:
            raise RuntimeError(f"LLM API call failed: {str(e)}")

    async def verify_connection(self) -> bool:
        """Verify LLM API connection is working."""
        self._ensure_configured()
        if not self.client:
            return False

        try:
            # Try a simple completion to verify connection
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,
            )
            return True
        except Exception:
            return False


# Global inference service instance (lazy initialization)
_inference_service = None

def get_inference_service():
    """Get or create inference service instance."""
    global _inference_service
    if _inference_service is None:
        _inference_service = InferenceService()
    return _inference_service

# Keep compatibility with existing imports
inference_service = get_inference_service()
