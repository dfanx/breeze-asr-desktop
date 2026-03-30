"""時間戳格式處理工具模組。"""


def seconds_to_timestamp(seconds: float) -> str:
    """將秒數轉為 HH:MM:SS.mmm 格式。"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def seconds_to_srt_timestamp(seconds: float) -> str:
    """將秒數轉為 SRT 格式 HH:MM:SS,mmm。"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
