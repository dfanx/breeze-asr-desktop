"""檔案相關工具模組。"""

import os
import re
from typing import List

SUPPORTED_EXTENSIONS = {".mp3", ".wav"}
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}


def is_supported_audio(path: str) -> bool:
    """判斷檔案是否為支援的音檔格式。"""
    _, ext = os.path.splitext(path)
    return ext.lower() in SUPPORTED_EXTENSIONS


def is_supported_video(path: str) -> bool:
    """判斷檔案是否為支援的影片格式。"""
    _, ext = os.path.splitext(path)
    return ext.lower() in SUPPORTED_VIDEO_EXTENSIONS


def is_supported_media(path: str) -> bool:
    """判斷檔案是否為支援的媒體格式（音檔或影片）。"""
    return is_supported_audio(path) or is_supported_video(path)


def safe_filename(name: str) -> str:
    """將檔名中不安全的字元替換為底線。"""
    return re.sub(r'[<>:"/\\|?*]', "_", name)


def scan_audio_files(folder: str, recursive: bool = False) -> List[str]:
    """掃描資料夾中的音檔，回傳完整路徑列表。"""
    results: List[str] = []
    if recursive:
        for root, _, files in os.walk(folder):
            for f in files:
                full = os.path.join(root, f)
                if is_supported_audio(full):
                    results.append(full)
    else:
        for f in os.listdir(folder):
            full = os.path.join(folder, f)
            if os.path.isfile(full) and is_supported_audio(full):
                results.append(full)
    return sorted(results)


def scan_media_files(folder: str, recursive: bool = False) -> List[str]:
    """掃描資料夾中的媒體檔案（音檔+影片），回傳完整路徑列表。"""
    results: List[str] = []
    if recursive:
        for root, _, files in os.walk(folder):
            for f in files:
                full = os.path.join(root, f)
                if is_supported_media(full):
                    results.append(full)
    else:
        for f in os.listdir(folder):
            full = os.path.join(folder, f)
            if os.path.isfile(full) and is_supported_media(full):
                results.append(full)
    return sorted(results)
