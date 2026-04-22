"""System monitoring service for CPU, memory, and GPU metrics."""

from typing import Dict, Any

from ..utils import get_logger

logger = get_logger(__name__)

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
    from pynvml import nvmlInit, nvmlDeviceGetHandleByIndex, nvmlDeviceGetUtilizationRates
    _PYNVML_AVAILABLE = True
except ImportError:
    _PYNVML_AVAILABLE = False


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
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "percent": mem.percent,
        }

    def get_gpu_stats(self) -> Dict[str, Any]:
        """Get GPU memory and utilization statistics."""
        if not _TORCH_AVAILABLE or not torch.cuda.is_available():
            return {"available": False, "cuda_available": False}

        gpu_count = torch.cuda.device_count()
        gpus = []

        for i in range(gpu_count):
            props = torch.cuda.get_device_properties(i)
            allocated_mb = torch.cuda.memory_allocated(i) / 1024 / 1024
            reserved_mb = torch.cuda.memory_reserved(i) / 1024 / 1024
            total_mb = props.total_memory / 1024 / 1024

            gpu_info = {
                "id": i,
                "name": props.name,
                "total_mb": round(total_mb, 0),
                "allocated_mb": round(allocated_mb, 0),
                "reserved_mb": round(reserved_mb, 0),
                "free_mb": round(total_mb - allocated_mb, 0),
                "utilization_percent": None,
            }

            if _PYNVML_AVAILABLE:
                try:
                    nvmlInit()
                    handle = nvmlDeviceGetHandleByIndex(i)
                    util = nvmlDeviceGetUtilizationRates(handle)
                    gpu_info["utilization_percent"] = util.gpu
                except Exception:
                    pass

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


monitoring_service = MonitoringService()
