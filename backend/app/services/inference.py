"""Inference service for style transfer using external LLM API."""

import os
import time
from typing import List, Optional
import httpx
from openai import AsyncOpenAI

from ..schemas import ChatMessage
from ..utils import get_logger
from ..db_operations import DatabaseOperations

logger = get_logger(__name__)

from config import settings

GENERATING_MOCK_MODE = settings.GENERATING_MOCK_MODE

# Local model imports (transformers + peft for LoRA adapter)
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel
    LOCAL_MODEL_AVAILABLE = True
except ImportError:
    LOCAL_MODEL_AVAILABLE = False
    logger.warning("transformers/peft not installed, local model inference disabled")

class InferenceService:
    """Service for calling external LLM API or local model for style transfer."""

    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self.model_name: str = "gpt-3.5-turbo"
        self._init_client()

        # Local model cache (style_id -> model)
        self._local_models: dict = {}
        self._base_model_name: Optional[str] = None
        self._tokenizer = None

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
        prompt = f"""请对用户输入进行回复。

用户输入：{requirement}

附带的文字：
{original_text}

请直接输出回复文本，不要添加任何解释说明。"""
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

    def _load_local_model(self, adapter_path: str, base_model_name: Optional[str] = None):
        """
        Load local base model with LoRA adapter.

        Args:
            adapter_path: Path to the LoRA adapter directory
            base_model_name: Base model name (e.g., 'Qwen/Qwen2.5-7B-Instruct')

        Returns:
            Tuple of (model, tokenizer)
        """
        if not LOCAL_MODEL_AVAILABLE:
            raise RuntimeError("transformers/peft not installed, cannot load local model")

        if base_model_name is None:
            raise RuntimeError("base_model_name is required for loading local model")

        logger.info(f"Loading local model: {base_model_name} with adapter: {adapter_path}")

        # Configure quantization (QLoRA 4-bit)
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16
        )

        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            base_model_name,
            trust_remote_code=True,
            padding_side="left"
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        # Load base model with quantization
        model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
            torch_dtype=torch.bfloat16,
        )

        # Load LoRA adapter
        if os.path.exists(adapter_path):
            model = PeftModel.from_pretrained(model, adapter_path)
            logger.info(f"Loaded LoRA adapter from: {adapter_path}")
        else:
            logger.warning(f"Adapter path not found: {adapter_path}, using base model only")

        model.eval()
        return model, tokenizer

    def get_style_model(self, style_id: str, adapter_path: Optional[str] = None, base_model_name: Optional[str] = None):
        """
        Get or load cached local model for a style.

        Args:
            style_id: Style ID for cache key
            adapter_path: Path to LoRA adapter
            base_model_name: Base model name (e.g., 'Qwen/Qwen2.5-7B-Instruct')

        Returns:
            Tuple of (model, tokenizer)
        """
        if style_id in self._local_models:
            return self._local_models[style_id]

        if adapter_path is None:
            # Default adapter path
            adapter_path = os.path.join(settings.MODELS_DIR, "adapters", style_id)

        model, tokenizer = self._load_local_model(adapter_path, base_model_name)
        self._local_models[style_id] = (model, tokenizer)
        return model, tokenizer

    async def get_adapter_path_from_db(self, style_id: str) -> Optional[str]:
        """
        Get adapter path from tasks table by style_id.

        Args:
            style_id: Style ID to look up

        Returns:
            Adapter path (result_path) or None if not found
        """
        db = DatabaseOperations(async_mode=True)
        try:
            # Get the latest completed task for this style
            task = await db.get_latest_task_by_style_async(style_id, status="COMPLETED")

            if task and task.result_path:
                logger.info(f"Found adapter path for style {style_id}: {task.result_path}")
                return task.result_path

            logger.warning(f"No completed task with adapter path found for style {style_id}")
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
                logger.info(f"Found base model for style {style_id}: {style.base_model}")
                return style.base_model
            raise RuntimeError(f"Base model not found for style {style_id}")
        finally:
            await db.close_async()

    async def generate_style_transfer(
        self,
        original_text: str,
        requirement: str,
        target_style: str,
        history: Optional[List[ChatMessage]] = None,
        style_id: Optional[str] = None,
    ) -> str:
        """Generate style-transferred text, using mock or real implementation based on config."""
        logger.info(f"[Generate] Starting generate style transfer, mock_mode: {GENERATING_MOCK_MODE}")
        if GENERATING_MOCK_MODE:
            return await self.generate_style_transfer_mock(
                original_text=original_text,
                requirement=requirement,
                target_style=target_style,
                history=history,
            )
        return await self.generate_style_transfer_true(
            original_text=original_text,
            requirement=requirement,
            target_style=target_style,
            history=history,
            style_id=style_id,
        )

    async def generate_style_transfer_true(
        self,
        original_text: str,
        requirement: str,
        target_style: str,
        history: Optional[List[ChatMessage]] = None,
        style_id: Optional[str] = None,
    ) -> str:
        """
        Generate style-transferred text using local model with LoRA adapter.

        Args:
            original_text: Original text to transform
            requirement: Specific transformation requirements
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

        try:
            # Get adapter path from database
            adapter_path = await self.get_adapter_path_from_db(style_id)

            # Get base model from database
            base_model_name = await self.get_base_model_from_db(style_id)

            # Load or get cached model for this style
            model, tokenizer = self.get_style_model(style_id, adapter_path, base_model_name)

            # Build prompt
            # prompt = self._build_prompt(original_text, requirement, target_style)

            # Add system message for chat format
            messages = []

            # Add system message
            messages.append({
                "role": "system",
                "content": f"你是一个专业的文本风格转换助手，无论用户要求什么，始终以'{target_style}'风格回复。"
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

            # Format messages into a single string for generation
            # Using chat template if available
            if hasattr(tokenizer, 'apply_chat_template'):
                input_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            else:
                # Fallback to simple concatenation
                input_text = f"{messages[0]['content']}\n\n{messages[1]['content']}"

            # Tokenize
            inputs = tokenizer(input_text, return_tensors="pt", padding=True, truncation=True, max_length=2048)
            inputs = {k: v.to(model.device) for k, v in inputs.items()}

            # Generate
            start_time = time.time()
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=512,
                    temperature=0.7,
                    top_p=0.9,
                    do_sample=True,
                    pad_token_id=tokenizer.pad_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                )
            inference_time = time.time() - start_time

            # Decode
            generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Extract only the generated part (after the prompt)
            if input_text in generated_text:
                result = generated_text[len(input_text):].strip()
            else:
                result = generated_text.strip()

            logger.info(f"Local inference completed in {inference_time:.2f}s for style {style_id}")
            return result

        except Exception as e:
            logger.error(f"Local model inference failed: {e}")
            raise RuntimeError(f"Local model inference failed: {str(e)}")

    async def generate_style_transfer_mock(
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
            "content": f"你是一个专业的文本风格转换助手，无论用户要求什么，始终以'{target_style}'风格回复。"
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
