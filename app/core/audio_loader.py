"""音檔載入模組 - 載入音檔並轉為標準 waveform。"""

import logging

import librosa
import numpy as np

from app.utils.file_utils import is_supported_audio

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000


def load_audio(path: str) -> tuple[np.ndarray, int]:
    """載入音檔並轉為 mono 16kHz waveform。

    Args:
        path: 音檔路徑。

    Returns:
        (waveform, sample_rate) — waveform 為 1D float32 numpy array。

    Raises:
        ValueError: 不支援的檔案格式。
        FileNotFoundError: 檔案不存在。
    """
    if not is_supported_audio(path):
        raise ValueError(f"不支援的音檔格式: {path}")

    logger.info("載入音檔: %s", path)
    waveform, sr = librosa.load(path, sr=SAMPLE_RATE, mono=True)
    logger.info("音檔載入完成: %.1f 秒", len(waveform) / sr)
    return waveform, sr
