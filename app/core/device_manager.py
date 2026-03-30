"""裝置管理模組 - 偵測 GPU/CPU 並選擇運算裝置。"""

import logging
from dataclasses import dataclass

import torch

from app.utils import json_utils, paths

logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """裝置資訊。"""

    device: str  # "cuda" or "cpu"
    dtype: torch.dtype  # float16 or float32
    device_name: str  # e.g. "NVIDIA GeForce RTX 4060" or "CPU"
    is_gpu_available: bool
    fallback_reason: str = ""  # 若 fallback 到 CPU 的原因


def get_device_info(prefer_gpu: bool | None = None) -> DeviceInfo:
    """偵測並回傳最適合的運算裝置資訊。

    Args:
        prefer_gpu: 是否偏好 GPU。None 時從 config 讀取。
    """
    if prefer_gpu is None:
        config = json_utils.load_json(paths.get_config_path(), {})
        prefer_gpu = config.get("prefer_gpu", True)

    if prefer_gpu and torch.cuda.is_available():
        try:
            device_name = torch.cuda.get_device_name(0)
            # 簡單測試 GPU 是否可用
            torch.tensor([1.0], device="cuda")
            logger.info("使用 GPU: %s", device_name)
            return DeviceInfo(
                device="cuda",
                dtype=torch.float16,
                device_name=device_name,
                is_gpu_available=True,
            )
        except Exception as e:
            reason = f"GPU 初始化失敗: {e}"
            logger.warning(reason)
            return DeviceInfo(
                device="cpu",
                dtype=torch.float32,
                device_name="CPU",
                is_gpu_available=False,
                fallback_reason=reason,
            )

    reason = ""
    if prefer_gpu and not torch.cuda.is_available():
        reason = "CUDA 不可用，退回 CPU"
        logger.info(reason)
    elif not prefer_gpu:
        logger.info("設定為使用 CPU")

    return DeviceInfo(
        device="cpu",
        dtype=torch.float32,
        device_name="CPU",
        is_gpu_available=torch.cuda.is_available(),
        fallback_reason=reason,
    )
