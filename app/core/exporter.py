"""輸出模組 - 匯出 txt / full.txt / srt。"""

import logging
import os

from app.core.transcriber import TranscriptionResult
from app.utils.time_utils import seconds_to_srt_timestamp, seconds_to_timestamp

logger = logging.getLogger(__name__)


def export_txt(result: TranscriptionResult, output_path: str) -> None:
    """匯出純文字整合結果。"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result.full_text)
    logger.info("已匯出: %s", output_path)


def export_full_txt(result: TranscriptionResult, output_path: str) -> None:
    """匯出帶時間戳的完整逐段結果。"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for seg in result.segments:
            start_ts = seconds_to_timestamp(seg.start)
            end_ts = seconds_to_timestamp(seg.end)
            f.write(f"[{start_ts} --> {end_ts}]\n{seg.text}\n\n")
    logger.info("已匯出: %s", output_path)


def export_srt(result: TranscriptionResult, output_path: str) -> None:
    """匯出 SRT 字幕檔。"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(result.segments, 1):
            start_ts = seconds_to_srt_timestamp(seg.start)
            end_ts = seconds_to_srt_timestamp(seg.end)
            f.write(f"{i}\n{start_ts} --> {end_ts}\n{seg.text}\n\n")
    logger.info("已匯出: %s", output_path)
