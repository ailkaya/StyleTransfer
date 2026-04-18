"""Inference service for style transfer using external LLM API."""

import re
import time
from typing import Dict, Optional, List
import httpx
import asyncio
import gc
from openai import AsyncOpenAI

from ..schemas import ChatMessage
from ..utils import get_logger, BASE_MODEL_MAP
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


class AdapterCacheItem:
    def __init__(self, model, last_used: float):
        self.model = model
        self.last_used = last_used


class AdapterManager:
    """
    管理多个 LoRA adapter（支持并发 + LRU + 显存控制）
    """

    def __init__(self, max_adapters: int = 3, max_gpu_mb: int = 14000):
        self.adapters: Dict[str, AdapterCacheItem] = {}
        self.max_adapters = max_adapters
        self.max_gpu_mb = max_gpu_mb
        self.lock = asyncio.Lock()
        logger.info(f"[AdapterManager] max_adapters: {max_adapters}, max_gpu_mb: {max_gpu_mb}")

    def _gpu_used_mb(self):
        if not torch.cuda.is_available():
            return 0
        return torch.cuda.memory_allocated() / 1024 / 1024

    def _evict_if_needed(self):
        """LRU + memory pressure eviction"""
        if len(self.adapters) <= self.max_adapters:
            return

        # 按 last_used 排序
        sorted_items = sorted(
            self.adapters.items(),
            key=lambda x: x[1].last_used
        )

        while len(sorted_items) > self.max_adapters:
            style_id, item = sorted_items.pop(0)
            del self.adapters[style_id]

            del item.model
            gc.collect()

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def get(self, style_id: str):
        style_id = str(style_id)
        item = self.adapters.get(style_id)
        if item:
            item.last_used = time.time()
            return item.model
        return None

    def set(self, style_id: str, model):
        style_id = str(style_id)
        self.adapters[style_id] = AdapterCacheItem(
            model=model,
            last_used=time.time()
        )
        self._evict_if_needed()


class InferenceService:

    def __init__(self):
        self.client = None
        self.model_name = None
        self._base_model = None
        self._tokenizer = None
        self._base_model_name = None

        self._init_client()

        max_adapters=3
        gpu_budget_mb = self._get_gpu_memory_budget()

        self.adapter_manager = AdapterManager(
            max_adapters=max_adapters,
            max_gpu_mb=gpu_budget_mb
        )
        logger.info(f"[Adapter] max_adapters={max_adapters}, max_gpu_mb={gpu_budget_mb}")

        self._lock = asyncio.Lock()

    def _get_gpu_memory_budget(self) -> float:
        """
        自动获取本机 GPU 显存，并计算可用于 adapter cache 的预算
        """

        if not torch.cuda.is_available():
            logger.info("[GPU] No CUDA device found, fallback to CPU mode")
            return 0

        # 当前 GPU
        device_count = torch.cuda.device_count()
        device_id = 0  # 默认用第一个 GPU

        total_mem = torch.cuda.get_device_properties(device_id).total_memory / 1024 / 1024

        # 预留系统 / CUDA / fragmentation 开销
        reserved_ratio = 0.30   # 30% 预留（很关键）

        usable_mem = total_mem * (1 - reserved_ratio)

        # 再保守一点：只允许 60% 用于 adapter cache
        adapter_budget = usable_mem * 0.6

        logger.info(f"[GPU] total={total_mem:.0f}MB, "
            f"usable={usable_mem:.0f}MB, "
            f"adapter_budget={adapter_budget:.0f}MB")

        return adapter_budget

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

    def _generate_system_prompt(self, style_tag: str) -> str:
        """根据风格配置生成系统提示词"""
        return f"你是<{style_tag}>的文章生成助手，擅长模仿该风格的写作特点。"

    def _build_prompt(
        self,
        original_text: str,
        requirement: str,
        target_style: str,
        task_type: str,
    ) -> str:
        """Build the prompt for style transfer."""
        prompt = f"""<|system|>
{self._generate_system_prompt(style_tag=target_style)}

<|style_tag|>
{target_style}

<|task|>
{task_type}

<|instruction|>
{requirement}

<|input|>
{original_text}
"""
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

    def _load_base_model(self, base_model_name: str):
        base_model_name = BASE_MODEL_MAP.get(base_model_name, base_model_name)

        if self._base_model_name == base_model_name:
            logger.info(f"[LoadBaseModel] {base_model_name} running")
            return self._tokenizer
        elif self._base_model_name is not None:
            self.unload_model()

        logger.info(f"[LoadBaseModel] loading {base_model_name}")

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16
        )

        tokenizer = AutoTokenizer.from_pretrained(
            base_model_name,
            trust_remote_code=True,
            padding_side="left"
        )

        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
            torch_dtype=torch.bfloat16,
            attn_implementation="sdpa",
        )

        model.eval()

        self._base_model = model
        self._tokenizer = tokenizer
        self._base_model_name = base_model_name

        return tokenizer
    
    def _load_adapter(self, adapter_path: str, style_id: str):
        """
        如果 cache 有 → 直接复用
        否则 → 加载新 adapter
        """
        style_id = str(style_id)

        cached = self.adapter_manager.get(style_id)
        if cached:
            logger.info(f"[LoRA] adapter {style_id} cached")
            return cached

        logger.info(f"[LoRA] loading adapter {style_id}")

        model = PeftModel.from_pretrained(
            self._base_model,
            adapter_path,
            adapter_name=style_id
        )

        self.adapter_manager.set(style_id, model)

        return model

    # def get_style_model(self, style_id: str, adapter_path: Optional[str] = None, base_model_name: Optional[str] = None):
    async def get_model(self, style_id: str, adapter_path: str, base_model_name: str):

        async with self._lock:

            # load base model if needed
            tokenizer = self._load_base_model(base_model_name)

            # load or reuse adapter
            model = self._load_adapter(adapter_path, style_id)

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
        if not torch.cuda.is_available():
            return

        used = torch.cuda.memory_allocated() / 1024 / 1024

        if used > self.adapter_manager.max_gpu_mb:
            logger.info("[WARN] GPU memory high, evicting adapters...")

            # 清 LRU
            self.adapter_manager._evict_if_needed()

            torch.cuda.empty_cache()
            gc.collect()

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
        original_text: str,
        requirement: str,
        target_style: str,
        task_type: str,
        history: Optional[List[ChatMessage]] = None,
        style_id: Optional[str] = None,
        use_api: bool = False,
    ) -> str:
        """Generate style-transferred text, using mock or real implementation based on config."""
        logger.info(f"[Generate] Starting generate, mock_mode: {GENERATING_MOCK_MODE}, use_api: {use_api}")
        if GENERATING_MOCK_MODE or use_api:
            return await self.generate_style_transfer_mock(
                original_text=original_text,
                requirement=requirement,
                target_style=target_style,
                task_type=task_type,
                history=history,
            )
        return await self.generate_style_transfer_true(
            original_text=original_text,
            requirement=requirement,
            target_style=target_style,
            task_type=task_type,
            history=history,
            style_id=style_id,
        )

    async def generate_style_transfer_true(
        self,
        original_text: str,
        requirement: str,
        target_style: str,
        task_type: str,
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

        style_id = str(style_id)

        try:
            # Get adapter path from database
            adapter_path = await self.get_adapter_path_from_db(style_id)

            # Get base model from database
            base_model_name = await self.get_base_model_from_db(style_id)

            # Load or get cached model for this style
            model, tokenizer = await self.get_model(style_id, adapter_path, base_model_name)

            logger.info(f"[Generate] model {base_model_name} and adapter {adapter_path} load successfully")

            # Add system message for chat format
            messages = []

            # Add system message
            messages.append({
                "role": "system",
                "content": self._generate_system_prompt(style_tag=target_style)
            })
            
            # Add history if provided
            if history:
                for msg in history:
                    messages.append({
                        "role": msg.role,
                        "content": msg.content,
                    })
            
            # Add user prompt
            prompt = self._build_prompt(original_text, requirement, target_style, task_type)
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

            self.check_memory_pressure()

            model.eval()

            inputs = tokenizer(
                input_text,
                return_tensors="pt",
                padding=False,
                truncation=True,
                max_length = 2048
            )

            inputs = {k: v.to(model.device) for k, v in inputs.items()}

            start_time = time.time()
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=512,
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.85,
                    eos_token_id=tokenizer.eos_token_id,
                    pad_token_id=tokenizer.pad_token_id,
                    repetition_penalty=1.02,
                    early_stopping=False,    
                )

            inference_time = time.time() - start_time

            # Decode
            input_length = inputs["input_ids"].shape[1]

            generated_ids = outputs[0][input_length:]
            result = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

            # print(result)
            result = re.sub(r"<think>.*?</think>", "", result, flags=re.DOTALL)

            logger.info(f"Local inference completed in {inference_time:.2f}s for style {style_id}")
            return result.strip()

        except Exception as e:
            logger.error(f"Local model inference failed: {e}")
            raise RuntimeError(f"Local model inference failed: {str(e)}")

    async def generate_style_transfer_mock(
        self,
        original_text: str,
        requirement: str,
        target_style: str,
        task_type: str,
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
        messages.append({
            "role": "user",
            "content": requirement,
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

        import gc
        import torch

        logger.info("[Unload] Starting model cleanup...")

        try:
            # 卸载 LoRA / PEFT wrapper
            if self._base_model is not None:
                try:
                    # PEFT模型可能有 active adapter
                    if hasattr(self._base_model, "disable_adapter"):
                        self._base_model.disable_adapter()

                    if hasattr(self._base_model, "active_adapters"):
                        self._base_model.active_adapters = None
                except Exception as e:
                    logger.warning(f"[Unload] adapter cleanup warning: {e}")

            # 删除 base model
            if self._base_model is not None:
                del self._base_model
                self._base_model = None

            # 删除 tokenizer
            if self._tokenizer is not None:
                del self._tokenizer
                self._tokenizer = None

            # 清空 adapter cache（关键）
            if hasattr(self, "adapter_manager"):
                if hasattr(self.adapter_manager, "adapters"):
                    for style_id, item in list(self.adapter_manager.adapters.items()):
                        try:
                            del item.model
                        except Exception:
                            pass

                    self.adapter_manager.adapters.clear()

            # 重置状态
            self._base_model_name = None

            # Python GC
            gc.collect()

            # CUDA cache 清理
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()

            logger.info("[Unload] Model cleanup completed successfully")

        except Exception as e:
            logger.error(f"[Unload] Failed to unload model: {e}")
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
