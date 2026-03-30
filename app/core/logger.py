"""日誌模組 - 檔案 + console + GUI callback 三合一 logging。"""

import logging
import os
from datetime import datetime
from typing import Callable, Optional

from app.utils.paths import get_logs_dir

_gui_callback: Optional[Callable[[str], None]] = None


class GUIHandler(logging.Handler):
    """將 log 訊息傳送到 GUI 的 handler。"""

    def emit(self, record: logging.LogRecord):
        if _gui_callback:
            msg = self.format(record)
            _gui_callback(msg)


def setup_logging(level: int = logging.INFO) -> None:
    """初始化日誌系統。"""
    logs_dir = get_logs_dir()
    os.makedirs(logs_dir, exist_ok=True)

    log_file = os.path.join(
        logs_dir, f"breeze_asr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )

    root = logging.getLogger()
    root.setLevel(level)

    # 檔案 handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    root.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    root.addHandler(ch)

    # GUI handler
    gh = GUIHandler()
    gh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    root.addHandler(gh)

    logging.info("日誌系統已初始化: %s", log_file)


def set_gui_callback(callback: Optional[Callable[[str], None]]) -> None:
    """設定 GUI log callback。"""
    global _gui_callback
    _gui_callback = callback
