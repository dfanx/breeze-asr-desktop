"""影片音軌抽取模組 - 從影片容器抽取音軌並轉為標準 WAV。"""

import json
import logging
import os
import shutil
import subprocess
import uuid

logger = logging.getLogger(__name__)

SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}


def is_supported_video(path: str) -> bool:
    """判斷檔案是否為支援的影片格式。"""
    _, ext = os.path.splitext(path)
    return ext.lower() in SUPPORTED_VIDEO_EXTENSIONS


def _get_ffmpeg_exe() -> str:
    """取得 ffmpeg 執行檔路徑。"""
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def _get_ffprobe_exe() -> str:
    """取得 ffprobe 執行檔路徑（與 ffmpeg 同目錄）。"""
    ffmpeg = _get_ffmpeg_exe()
    ffprobe = os.path.join(os.path.dirname(ffmpeg), ffmpeg.replace("ffmpeg", "ffprobe"))
    if os.path.isfile(ffprobe):
        return ffprobe
    # fallback: 用 ffmpeg -i 方式偵測，不需要 ffprobe
    return ""


def _has_audio_stream(video_path: str) -> bool:
    """檢查影片是否包含音軌。"""
    ffprobe = _get_ffprobe_exe()
    if ffprobe:
        try:
            result = subprocess.run(
                [
                    ffprobe,
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_streams",
                    "-select_streams", "a",
                    video_path,
                ],
                capture_output=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            stdout = result.stdout.decode("utf-8", errors="replace")
            data = json.loads(stdout)
            return len(data.get("streams", [])) > 0
        except Exception:
            pass

    # fallback: 用 ffmpeg 嘗試讀取，檢查 stderr 是否有 audio stream
    try:
        ffmpeg = _get_ffmpeg_exe()
        result = subprocess.run(
            [ffmpeg, "-i", video_path, "-hide_banner"],
            capture_output=True,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        stderr = result.stderr.decode("utf-8", errors="replace")
        return "Audio:" in stderr
    except Exception:
        return False


def extract_audio(video_path: str, temp_dir: str) -> str:
    """從影片抽取第一條音軌並轉為 16kHz mono WAV。

    Args:
        video_path: 影片檔案路徑。
        temp_dir: 暫存目錄路徑。

    Returns:
        暫存 WAV 檔案路徑。

    Raises:
        ValueError: 影片不包含音軌。
        RuntimeError: ffmpeg 抽取失敗。
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"影片檔案不存在: {video_path}")

    if not _has_audio_stream(video_path):
        raise ValueError(f"此影片未包含可用音軌: {os.path.basename(video_path)}")

    os.makedirs(temp_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    temp_filename = f"{base_name}_{uuid.uuid4().hex[:8]}.wav"
    temp_path = os.path.join(temp_dir, temp_filename)

    ffmpeg = _get_ffmpeg_exe()

    cmd = [
        ffmpeg,
        "-i", video_path,
        "-vn",                  # 不處理視訊
        "-acodec", "pcm_s16le", # 輸出 PCM 16-bit
        "-ar", "16000",         # 16kHz
        "-ac", "1",             # mono
        "-y",                   # 覆寫
        temp_path,
    ]

    logger.info("抽取音軌: %s", os.path.basename(video_path))
    logger.debug("ffmpeg 命令: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=600,  # 10 分鐘超時
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        _safe_remove(temp_path)
        raise RuntimeError(f"音軌抽取超時: {os.path.basename(video_path)}")

    if result.returncode != 0:
        _safe_remove(temp_path)
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(
            f"音軌抽取失敗: {os.path.basename(video_path)}\n{stderr[-500:]}"
        )

    if not os.path.isfile(temp_path) or os.path.getsize(temp_path) == 0:
        _safe_remove(temp_path)
        raise RuntimeError(f"音軌抽取產生空檔案: {os.path.basename(video_path)}")

    logger.info("音軌抽取完成: %s -> %s", os.path.basename(video_path), temp_filename)
    return temp_path


def cleanup_temp_dir(temp_dir: str) -> None:
    """清理暫存目錄中的所有檔案。"""
    if os.path.isdir(temp_dir):
        for f in os.listdir(temp_dir):
            _safe_remove(os.path.join(temp_dir, f))
        logger.debug("已清理暫存目錄: %s", temp_dir)


def _safe_remove(path: str) -> None:
    """安全刪除檔案。"""
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass
