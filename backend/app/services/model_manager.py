"""Global model manager for shared base model and adapter loading.

Prevents duplicate loading of the same base model across inference and training,
and provides centralized LRU adapter cache with GPU memory pressure control.
"""

import gc
import time
import threading
from typing import Optional, Tuple, Any, Dict

from ..utils import get_logger, BASE_MODEL_MAP

logger = get_logger(__name__)

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    _TRANSFORMERS_AVAILABLE = True
except ImportError:
    _TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers not installed, model manager disabled")


class _BaseModelCacheItem:
    """Cached base model entry with reference counting."""

    def __init__(self, model: Any, tokenizer: Any):
        self.model = model
        self.tokenizer = tokenizer
        self.ref_count = 1


class _AdapterCacheItem:
    """Cached adapter entry with LRU tracking."""

    def __init__(self, model: Any, base_model_name: str):
        self.model = model
        self.base_model_name = base_model_name
        self.last_used = time.time()


class GlobalModelManager:
    """Singleton global manager for loading and caching base LLMs and LoRA adapters.

    Ensures each unique base model is loaded at most once in the process,
    shared between inference and training services. Adapters are cached
    separately with LRU eviction and GPU memory pressure control.
    """

    _instance: Optional["GlobalModelManager"] = None
    _init_lock = threading.Lock()

    def __new__(cls) -> "GlobalModelManager":
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        self._base_cache: Dict[str, _BaseModelCacheItem] = {}
        self._base_lock = threading.Lock()

        self._adapter_cache: Dict[str, _AdapterCacheItem] = {}
        self._adapter_lock = threading.Lock()
        self._max_adapters = 3

    # ==================== GPU Budget ====================

    def _get_gpu_budget_mb(self) -> float:
        """动态探测 GPU 总显存，预留 15%-20% 后返回可用预算。"""
        if not torch.cuda.is_available():
            return 0.0

        from config import settings
        device_id = 0
        total_mb = torch.cuda.get_device_properties(device_id).total_memory / 1024 / 1024
        # 读取 config 中的预留比例，钳制在 15%-20%
        reserved_ratio = max(0.15, min(0.20, settings.MODEL_RESERVED_GPU_RATIO))
        budget_mb = total_mb * (1 - reserved_ratio)
        logger.debug(
            f"[ModelManager] GPU budget: total={total_mb:.0f}MB, "
            f"reserved_ratio={reserved_ratio:.0%}, budget={budget_mb:.0f}MB"
        )
        return budget_mb

    # ==================== Base Model ====================

    def load_model(
        self,
        model_name: str,
        padding_side: Optional[str] = None,
        attn_implementation: Optional[str] = None,
    ) -> Tuple[Any, Any]:
        """Load a base model and tokenizer, or return cached ones.

        Args:
            model_name: HuggingFace model name or alias.
            padding_side: Tokenizer padding side (e.g. "left" for inference).
            attn_implementation: Attention implementation (e.g. "sdpa").

        Returns:
            Tuple of (model, tokenizer).

        Raises:
            RuntimeError: If transformers is not installed.
        """
        if not _TRANSFORMERS_AVAILABLE:
            raise RuntimeError("transformers library is required for model loading")

        resolved_name = BASE_MODEL_MAP.get(model_name, model_name)

        with self._base_lock:
            cached = self._base_cache.get(resolved_name)
            if cached is not None:
                cached.ref_count += 1
                logger.info(f"[ModelManager] base cache hit: {resolved_name} (refs={cached.ref_count})")
                return cached.model, cached.tokenizer

        logger.info(f"[ModelManager] loading base: {resolved_name}")

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )

        tokenizer_kwargs = {"trust_remote_code": True}
        if padding_side is not None:
            tokenizer_kwargs["padding_side"] = padding_side

        tokenizer = AutoTokenizer.from_pretrained(resolved_name, **tokenizer_kwargs)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model_kwargs = {
            "quantization_config": bnb_config,
            "device_map": "auto",
            "trust_remote_code": True,
            "torch_dtype": torch.bfloat16,
        }
        if attn_implementation is not None:
            model_kwargs["attn_implementation"] = attn_implementation

        model = AutoModelForCausalLM.from_pretrained(resolved_name, **model_kwargs)

        with self._base_lock:
            # Double-check in case another thread loaded it while we were loading
            if resolved_name in self._base_cache:
                cached = self._base_cache[resolved_name]
                cached.ref_count += 1
                # Clean up the one we just loaded to avoid duplicate memory
                del model
                del tokenizer
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                logger.info(f"[ModelManager] raced load for {resolved_name}, using cached")
                return cached.model, cached.tokenizer

            self._base_cache[resolved_name] = _BaseModelCacheItem(model, tokenizer)
            logger.info(f"[ModelManager] base loaded: {resolved_name}")

        self.check_memory_pressure()
        return model, tokenizer

    def get_model(self, model_name: str) -> Optional[Tuple[Any, Any]]:
        """Get cached base model without incrementing ref count, or None."""
        resolved_name = BASE_MODEL_MAP.get(model_name, model_name)
        with self._base_lock:
            cached = self._base_cache.get(resolved_name)
            if cached is not None:
                return cached.model, cached.tokenizer
        return None

    def get_tokenizer(self, model_name: str) -> Optional[Any]:
        """Get cached tokenizer without incrementing ref count, or None."""
        resolved_name = BASE_MODEL_MAP.get(model_name, model_name)
        with self._base_lock:
            cached = self._base_cache.get(resolved_name)
            if cached is not None:
                return cached.tokenizer
        return None

    def unload_model(self, model_name: str) -> bool:
        """Decrement ref count and unload base model if no references remain.

        Returns:
            True if model was actually unloaded.
        """
        resolved_name = BASE_MODEL_MAP.get(model_name, model_name)

        with self._base_lock:
            cached = self._base_cache.get(resolved_name)
            if cached is None:
                logger.warning(f"[ModelManager] unload called for unknown model: {resolved_name}")
                return False

            cached.ref_count -= 1
            logger.info(f"[ModelManager] release base {resolved_name} (refs={cached.ref_count})")

            if cached.ref_count > 0:
                return False

            del self._base_cache[resolved_name]

        # Release outside the lock to avoid holding lock during GC
        del cached.model
        del cached.tokenizer
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info(f"[ModelManager] base unloaded: {resolved_name}")
        return True

    # ==================== Adapter ====================

    def load_adapter(
        self,
        style_id: str,
        adapter_path: str,
        base_model_name: str,
        padding_side: Optional[str] = None,
        attn_implementation: Optional[str] = None,
    ) -> Tuple[Any, Any]:
        """Load or get cached LoRA adapter.

        Args:
            style_id: Unique style identifier (used as cache key).
            adapter_path: Path to the PEFT adapter weights.
            base_model_name: Base model name or alias.
            padding_side: Tokenizer padding side.
            attn_implementation: Attention implementation.

        Returns:
            Tuple of (adapter_model, tokenizer).

        Raises:
            RuntimeError: If peft/transformers is not installed.
        """
        try:
            from peft import PeftModel
        except ImportError as e:
            raise RuntimeError("peft library is required for adapter loading") from e

        style_id = str(style_id)

        with self._adapter_lock:
            cached = self._adapter_cache.get(style_id)
            if cached is not None:
                cached.last_used = time.time()
                logger.info(f"[ModelManager] adapter cache hit: {style_id}")
                tokenizer = self._get_tokenizer_unsafe(cached.base_model_name)
                return cached.model, tokenizer

            # Load base model first (increments ref_count)
            base_model, tokenizer = self.load_model(
                base_model_name,
                padding_side=padding_side,
                attn_implementation=attn_implementation,
            )

            logger.info(f"[ModelManager] loading adapter: {style_id}")
            model = PeftModel.from_pretrained(
                base_model,
                adapter_path,
                adapter_name=style_id,
            )
            model.eval()

            self._adapter_cache[style_id] = _AdapterCacheItem(model, base_model_name)
            self._evict_adapters_if_needed()

        self.check_memory_pressure()
        return model, tokenizer

    def get_adapter(self, style_id: str) -> Optional[Tuple[Any, Any]]:
        """Get cached adapter without loading, or None.

        Returns:
            Tuple of (adapter_model, tokenizer) or None.
        """
        style_id = str(style_id)
        with self._adapter_lock:
            cached = self._adapter_cache.get(style_id)
            if cached is not None:
                cached.last_used = time.time()
                tokenizer = self._get_tokenizer_unsafe(cached.base_model_name)
                return cached.model, tokenizer
        return None

    def unload_adapter(self, style_id: str) -> bool:
        """Unload a specific adapter from cache and release base model ref.

        Returns:
            True if adapter was actually unloaded.
        """
        style_id = str(style_id)
        with self._adapter_lock:
            cached = self._adapter_cache.get(style_id)
            if cached is None:
                return False
            base_model_name = cached.base_model_name
            del self._adapter_cache[style_id]

        del cached.model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        self.unload_model(base_model_name)
        logger.info(f"[ModelManager] adapter unloaded: {style_id}")
        return True

    def unload_all_adapters(self) -> int:
        """Unload all cached adapters.

        Returns:
            Number of adapters unloaded.
        """
        with self._adapter_lock:
            items = list(self._adapter_cache.items())
            self._adapter_cache.clear()

        count = 0
        base_models: set[str] = set()
        for style_id, cached in items:
            try:
                del cached.model
                count += 1
                base_models.add(cached.base_model_name)
                logger.info(f"[ModelManager] adapter unloaded: {style_id}")
            except Exception as e:
                logger.error(f"[ModelManager] failed to unload adapter {style_id}: {e}")

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        for bm in base_models:
            self.unload_model(bm)

        return count

    def _evict_adapters_if_needed(self):
        """LRU eviction: remove oldest adapters if cache exceeds max size."""
        while len(self._adapter_cache) > self._max_adapters:
            sorted_items = sorted(
                self._adapter_cache.items(),
                key=lambda x: x[1].last_used,
            )
            style_id, item = sorted_items[0]
            self.unload_adapter(style_id)

    def check_memory_pressure(self):
        """Check GPU memory usage and evict adapters if over budget."""
        if not torch.cuda.is_available():
            return

        used_mb = torch.cuda.memory_allocated() / 1024 / 1024
        budget_mb = self._get_gpu_budget_mb()
        if used_mb > budget_mb:
            logger.warning(
                f"[ModelManager] GPU memory high ({used_mb:.0f}MB > {budget_mb:.0f}MB), "
                "evicting adapters..."
            )
            self._evict_adapters_if_needed()
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def _get_tokenizer_unsafe(self, base_model_name: str) -> Optional[Any]:
        """Get tokenizer from base cache without acquiring lock.

        Caller must already hold _adapter_lock or _base_lock.
        """
        resolved_name = BASE_MODEL_MAP.get(base_model_name, base_model_name)
        cached = self._base_cache.get(resolved_name)
        if cached is not None:
            return cached.tokenizer
        return None

    # ==================== Combined ====================

    def unload_all(self) -> int:
        """Unload all adapters and base models regardless of ref count.

        Returns:
            Total number of items unloaded.
        """
        # Adapters first
        adapter_count = self.unload_all_adapters()

        # Base models
        with self._base_lock:
            base_items = list(self._base_cache.items())
            self._base_cache.clear()

        base_count = 0
        for name, cached in base_items:
            try:
                del cached.model
                del cached.tokenizer
                base_count += 1
                logger.info(f"[ModelManager] base force unloaded: {name}")
            except Exception as e:
                logger.error(f"[ModelManager] failed to unload base {name}: {e}")

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        return adapter_count + base_count

    def list_loaded(self) -> Dict[str, int]:
        """Return dict of loaded base model names to their ref counts."""
        with self._base_lock:
            return {name: item.ref_count for name, item in self._base_cache.items()}

    def list_loaded_adapters(self) -> Dict[str, str]:
        """Return dict of loaded adapter style_ids to their base model names."""
        with self._adapter_lock:
            return {sid: item.base_model_name for sid, item in self._adapter_cache.items()}


# Global singleton instance
model_manager = GlobalModelManager()
