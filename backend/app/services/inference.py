"""Inference service for style transfer using external LLM API."""

import re
import time
from typing import Dict, Optional, List
import httpx
from openai import AsyncOpenAI

from ..schemas import ChatMessage
from ..utils import get_logger, BASE_MODEL_MAP
from ..db_operations import DatabaseOperations
from .model_manager import model_manager

logger = get_logger(__name__)

from config import settings

GENERATING_MOCK_MODE = settings.GENERATING_MOCK_MODE
ENABLE_MESSAGE_HISTORY = settings.ENABLE_MESSAGE_HISTORY

# Local model imports (transformers + peft for LoRA adapter)
try:
    import torch
    LOCAL_MODEL_AVAILABLE = True
except ImportError:
    LOCAL_MODEL_AVAILABLE = False
    logger.warning("transformers/peft not installed, local model inference disabled")


class InferenceService:

    def __init__(self):
        self.client = None
        self.model_name = None

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

    def _generate_system_prompt(self, style_tag: str) -> str:
        """根据风格配置生成系统提示词"""
        return f"你是<{style_tag}>的文章生成助手，擅长模仿该风格的写作特点。请根据用户要求生成文本，保持该风格的一致性。不要使用深度思考。"

    def _build_messages_with_history(
        self,
        system_prompt: str,
        history: Optional[List[ChatMessage]],
        current_input: str,
    ) -> List[Dict]:
        """Build chat messages with history collapsed into a single context string.

        History is appended to the system prompt so the model sees it as background
        reference only. The current request is sent as a standalone user message to
        prevent the model from confusing historical turns with the present request.
        """
        messages = []

        full_system = system_prompt
        if history and ENABLE_MESSAGE_HISTORY:
            history_parts = []
            for i, msg in enumerate(history, 1):
                history_parts.append(f"[对话记录 {i}] {msg.content}")
            history_text = "\n".join(history_parts)
            full_system += (
                f"\n\n===== 以下是你的历史对话记录，仅供参考 =====\n"
                f"{history_text}\n"
                f"===== 历史记录结束，请仅处理下面的用户输入 ====="
            )

        messages.append({"role": "system", "content": full_system})
        messages.append({"role": "user", "content": current_input})

        return messages

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

    async def get_model(self, style_id: str, adapter_path: str, base_model_name: str):
        model, tokenizer = model_manager.load_adapter(
            style_id=style_id,
            adapter_path=adapter_path,
            base_model_name=base_model_name,
            padding_side="left",
            attn_implementation="sdpa",
        )
        return model, tokenizer
        
    def get_gpu_stats(self):
        if not torch.cuda.is_available():
            return {"gpu": False}

        return {
            "allocated_mb": torch.cuda.memory_allocated() / 1024 / 1024,
            "reserved_mb": torch.cuda.memory_reserved() / 1024 / 1024,
            "max_mb": torch.cuda.max_memory_allocated() / 1024 / 1024
        }
    
    def check_memory_pressure(self):
        model_manager.check_memory_pressure()

    async def get_adapter_path_from_db(self, style_id: str) -> Optional[str]:
        """
        Get adapter path from styles table by style_id.

        Args:
            style_id: Style ID to look up

        Returns:
            Adapter path or None if not found
        """
        db = DatabaseOperations(async_mode=True)
        try:
            style = await db.get_style_async(style_id)

            if style and style.adapter_path:
                logger.info(f"Found adapter path for style {style_id}: {style.adapter_path}")
                return style.adapter_path

            logger.warning(f"No adapter path found for style {style_id}")
            return None
        finally:
            await db.close_async()

    async def get_base_model_from_db(self, style_id: str) -> str:
        """
        Get base model name from styles table.

        Args:
            style_id: Style ID to look up

        Returns:
            Base model name

        Raises:
            RuntimeError: If style not found or base_model not set
        """
        db = DatabaseOperations(async_mode=True)
        try:
            style = await db.get_style_async(style_id)
            if style and style.base_model:
                mapped = BASE_MODEL_MAP.get(style.base_model, style.base_model)
                logger.info(f"Found base model for style {style_id}: {mapped}")
                return mapped
            raise RuntimeError(f"Base model not found for style {style_id}")
        finally:
            await db.close_async()

    async def generate_style_transfer(
        self,
        input: str,
        target_style: str,
        history: Optional[List[ChatMessage]] = None,
        style_id: Optional[str] = None,
        use_api: bool = False,
    ) -> str:
        """Generate style-transferred text, using mock or real implementation based on config."""
        logger.info(f"[Generate] Starting generate, mock_mode: {GENERATING_MOCK_MODE}, use_api: {use_api}")
        if GENERATING_MOCK_MODE or use_api:
            return await self.generate_style_transfer_mock(
                input=input,
                target_style=target_style,
                history=history,
            )
        return await self.generate_style_transfer_true(
            input=input,
            target_style=target_style,
            history=history,
            style_id=style_id,
        )

    async def generate_style_transfer_true(
        self,
        input: str,
        target_style: str,
        history: Optional[List[ChatMessage]] = None,
        style_id: Optional[str] = None,
    ) -> str:
        """
        Generate style-transferred text using local model with LoRA adapter.

        Args:
            input: User input text
            target_style: Target style name
            history: Optional chat history for context
            style_id: Style ID for loading LoRA adapter

        Returns:
            Transformed text

        Raises:
            ValueError: If local model is not available
            RuntimeError: If inference fails
        """
        if not LOCAL_MODEL_AVAILABLE:
            raise ValueError(
                "Local model inference not available. "
                "Please install transformers and peft: pip install transformers peft accelerate bitsandbytes"
            )

        if not style_id:
            raise ValueError("style_id is required for local model inference")

        style_id = str(style_id)

        try:
            # Get adapter path from database
            adapter_path = await self.get_adapter_path_from_db(style_id)

            # Get base model from database
            base_model_name = await self.get_base_model_from_db(style_id)

            # Load or get cached model for this style
            model, tokenizer = await self.get_model(style_id, adapter_path, base_model_name)

            logger.info(f"[Generate] model {base_model_name} and adapter {adapter_path} load successfully")

            messages = self._build_messages_with_history(
                system_prompt=self._generate_system_prompt(style_tag=target_style),
                history=history,
                current_input=input,
            )

            # Format messages into a single string for generation
            # Using chat template if available
            if hasattr(tokenizer, 'apply_chat_template'):
                input_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            else:
                # Fallback to simple concatenation
                input_text = f"{messages[0]['content']}\n\n{messages[1]['content']}"

            self.check_memory_pressure()

            model.eval()

            inputs = tokenizer(
                input_text,
                return_tensors="pt",
                padding=False,
                truncation=True,
                max_length = 1024
            )

            inputs = {k: v.to(model.device) for k, v in inputs.items()}

            start_time = time.time()
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=196,
                    do_sample=True,
                    temperature=0.8,
                    top_p=0.9,
                    top_k=50,
                    eos_token_id=tokenizer.eos_token_id,
                    pad_token_id=tokenizer.pad_token_id,
                    repetition_penalty=1.1,
                    early_stopping=False,    
                )

            inference_time = time.time() - start_time

            # Decode
            input_length = inputs["input_ids"].shape[1]

            generated_ids = outputs[0][input_length:]
            result = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

            # print(result)
            result = re.sub(r"<think>.*?</think>", "", result.strip(), flags=re.DOTALL)

            logger.info(f"Local inference completed in {inference_time:.2f}s for style {style_id}")
            return result.strip()

        except Exception as e:
            logger.error(f"Local model inference failed: {e}")
            raise RuntimeError(f"Local model inference failed: {str(e)}")

    async def generate_style_transfer_mock(
        self,
        input: str,
        target_style: str,
        history: Optional[List[ChatMessage]] = None,
    ) -> str:
        """
        Generate style-transferred text using external LLM API.

        Args:
            input: User input text
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

        messages = self._build_messages_with_history(
            system_prompt=self._generate_system_prompt(target_style),
            history=history,
            current_input=input,
        )

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

    async def call_llm_raw(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        """通用 LLM 调用方法，供预处理等模块使用。"""
        self._ensure_configured()
        if not self.client:
            raise ValueError("LLM client not configured")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM raw call failed: {e}")
            raise

    async def call_llm_for_validation(self, prompt: str) -> str:
        """调用 LLM 进行验证类任务（如判断 comment 语义有效性）。"""
        self._ensure_configured()
        if not self.client:
            raise ValueError("LLM client not configured")

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一个文本分析助手，只回答 VALID 或 INVALID。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=10,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM validation call failed: {e}")
            raise

    async def call_llm_for_adjustment(self, prompt: str) -> str:
        """调用 LLM 进行调整类任务（如根据 comment 调整训练样本）。"""
        self._ensure_configured()
        if not self.client:
            raise ValueError("LLM client not configured")

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一个训练数据优化助手。根据用户要求调整数据，只输出JSON格式。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2048,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM adjustment call failed: {e}")
            raise

    def unload_model(self):
        if not GENERATING_MOCK_MODE:
            self.unload_model_true()

    def unload_model_true(self):
        """
        卸载当前运行的模型（base model + adapters + tokenizer）
        用于释放 GPU 显存
        """
        logger.info("[Unload] unload_model_true is deprecated; ModelManager handles eviction automatically.")

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
