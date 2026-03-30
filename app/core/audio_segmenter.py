"""音檔切段模組 - 依設定將音檔切成多段。"""

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class AudioSegment:
    """音檔片段。"""

    start: float  # 開始秒數
    end: float  # 結束秒數
    waveform: np.ndarray  # 該段的 waveform


def split_audio(
    waveform: np.ndarray, sample_rate: int, segment_seconds: int = 30
) -> list[AudioSegment]:
    """將音檔依秒數切段。

    Args:
        waveform: 1D float32 numpy array。
        sample_rate: 取樣率。
        segment_seconds: 每段秒數。

    Returns:
        AudioSegment 列表。
    """
    total_samples = len(waveform)
    segment_samples = segment_seconds * sample_rate
    segments: list[AudioSegment] = []

    for start_sample in range(0, total_samples, segment_samples):
        end_sample = min(start_sample + segment_samples, total_samples)
        start_sec = start_sample / sample_rate
        end_sec = end_sample / sample_rate
        segments.append(
            AudioSegment(
                start=start_sec,
                end=end_sec,
                waveform=waveform[start_sample:end_sample],
            )
        )

    logger.info("音檔切段完成: %d 段 (每段 %d 秒)", len(segments), segment_seconds)
    return segments
