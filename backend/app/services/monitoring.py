"""System monitoring service for CPU, memory, and GPU metrics."""

from typing import Dict, Any

from ..utils import get_logger

logger = get_logger(__name__)

# ------------------------
# Optional dependencies
# ------------------------

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False
    logger.warning("psutil not installed, CPU/memory monitoring disabled")

try:
    import torch
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False
    logger.warning("torch not installed, GPU monitoring disabled")

try:
    from pynvml import (
        nvmlInit,
        nvmlShutdown,
        nvmlDeviceGetHandleByIndex,
        nvmlDeviceGetUtilizationRates,
        nvmlDeviceGetMemoryInfo,
    )
    _PYNVML_AVAILABLE = True
except ImportError:
    _PYNVML_AVAILABLE = False
    logger.warning("pynvml not installed, detailed GPU monitoring disabled")


# ------------------------
# NVML lifecycle management
# ------------------------

_NVML_INITIALIZED = False


def _init_nvml() -> bool:
    """Initialize NVML once (lazy init)."""
    global _NVML_INITIALIZED

    if not _PYNVML_AVAILABLE:
        return False

    if not _NVML_INITIALIZED:
        try:
            nvmlInit()
            _NVML_INITIALIZED = True
        except Exception as e:
            logger.warning(f"NVML init failed: {e}")
            return False

    return True


def _shutdown_nvml():
    """Shutdown NVML safely."""
    global _NVML_INITIALIZED

    if _NVML_INITIALIZED:
        try:
            nvmlShutdown()
        except Exception:
            pass
        finally:
            _NVML_INITIALIZED = False


# 自动注册退出清理（可选但推荐）
try:
    import atexit
    atexit.register(_shutdown_nvml)
except Exception:
    pass


# ------------------------
# Monitoring Service
# ------------------------

class MonitoringService:
    """Service for collecting real-time system metrics."""

    def get_cpu_stats(self) -> Dict[str, Any]:
        """Get CPU usage statistics."""
        if not _PSUTIL_AVAILABLE:
            return {"available": False}

        freq = psutil.cpu_freq()

        return {
            "available": True,
            "percent": psutil.cpu_percent(interval=0.1),
            "count": {
                "logical": psutil.cpu_count(logical=True),
                "physical": psutil.cpu_count(logical=False),
            },
            "freq_mhz": round(freq.current, 0) if freq else None,
        }

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get system memory statistics."""
        if not _PSUTIL_AVAILABLE:
            return {"available": False}

        mem = psutil.virtual_memory()

        return {
            "available": True,
            "total_gb": round(mem.total / (1024 ** 3), 2),
            "available_gb": round(mem.available / (1024 ** 3), 2),
            "used_gb": round(mem.used / (1024 ** 3), 2),
            "percent": mem.percent,
        }

    def get_gpu_stats(self) -> Dict[str, Any]:
        """Get GPU memory and utilization statistics."""
        if not _TORCH_AVAILABLE or not torch.cuda.is_available():
            return {"available": False, "cuda_available": False}

        gpu_count = torch.cuda.device_count()
        gpus = []

        # 初始化 NVML（只会执行一次）
        nvml_ok = _init_nvml()

        for i in range(gpu_count):
            props = torch.cuda.get_device_properties(i)
            total_mb = props.total_memory / 1024 / 1024

            gpu_info = {
                "id": i,
                "name": props.name,
                "total_mb": round(total_mb, 0),
                "allocated_mb": None,
                "reserved_mb": None,
                "free_mb": None,
                "utilization_percent": None,
            }

            # ------------------------
            # 优先使用 NVML（真实 GPU 使用情况）
            # ------------------------
            if nvml_ok:
                try:
                    handle = nvmlDeviceGetHandleByIndex(i)
                    mem_info = nvmlDeviceGetMemoryInfo(handle)
                    util = nvmlDeviceGetUtilizationRates(handle)

                    gpu_info["total_mb"] = round(mem_info.total / 1024 / 1024, 0)
                    gpu_info["allocated_mb"] = round(mem_info.used / 1024 / 1024, 0)
                    gpu_info["free_mb"] = round(mem_info.free / 1024 / 1024, 0)
                    gpu_info["utilization_percent"] = util.gpu

                except Exception as e:
                    logger.warning(f"NVML read failed for GPU {i}: {e}")

            # ------------------------
            # fallback：torch（仅当前进程）
            # ------------------------
            if gpu_info["allocated_mb"] is None:
                try:
                    allocated_mb = torch.cuda.memory_allocated(i) / 1024 / 1024
                    reserved_mb = torch.cuda.memory_reserved(i) / 1024 / 1024

                    gpu_info["allocated_mb"] = round(allocated_mb, 0)
                    gpu_info["reserved_mb"] = round(reserved_mb, 0)
                    gpu_info["free_mb"] = round(total_mb - allocated_mb, 0)

                except Exception as e:
                    logger.warning(f"torch fallback failed for GPU {i}: {e}")

            gpus.append(gpu_info)

        return {
            "available": True,
            "cuda_available": True,
            "count": gpu_count,
            "gpus": gpus,
        }

    def get_all_stats(self) -> Dict[str, Any]:
        """Get all system statistics."""
        return {
            "cpu": self.get_cpu_stats(),
            "memory": self.get_memory_stats(),
            "gpu": self.get_gpu_stats(),
        }


# ------------------------
# Singleton instance
# ------------------------

monitoring_service = MonitoringService()