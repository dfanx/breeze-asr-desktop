"""模型下載器模組 - 從 HuggingFace Hub 下載模型。"""

import logging
import os
import time

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


class DownloadWorker(QThread):
    """背景下載 Worker。"""

    progress_updated = Signal(float)  # 0.0 ~ 1.0
    status_updated = Signal(str)  # 狀態文字
    download_finished = Signal(str)  # local_path
    download_failed = Signal(str)  # error_message
    download_canceled = Signal()

    def __init__(self, hf_repo: str, local_dir: str, parent=None):
        super().__init__(parent)
        self._hf_repo = hf_repo
        self._local_dir = local_dir
        self._canceled = False

    def cancel(self) -> None:
        """取消下載。"""
        self._canceled = True

    def run(self) -> None:
        """執行下載（在背景執行緒）。"""
        from huggingface_hub import snapshot_download
        from huggingface_hub.utils import (
            HfHubHTTPError,
            LocalEntryNotFoundError,
        )

        os.makedirs(self._local_dir, exist_ok=True)

        for attempt in range(1, MAX_RETRIES + 1):
            if self._canceled:
                self.download_canceled.emit()
                return

            try:
                self.status_updated.emit(
                    f"下載中（第 {attempt}/{MAX_RETRIES} 次嘗試）..."
                )
                self.progress_updated.emit(0.0)

                local_path = snapshot_download(
                    repo_id=self._hf_repo,
                    local_dir=self._local_dir,
                    resume_download=True,
                )

                if self._canceled:
                    self.download_canceled.emit()
                    return

                self.progress_updated.emit(1.0)
                self.status_updated.emit("下載完成")
                self.download_finished.emit(local_path)
                return

            except (HfHubHTTPError, LocalEntryNotFoundError, OSError) as e:
                logger.warning("下載失敗 (第 %d 次): %s", attempt, e)
                if attempt < MAX_RETRIES:
                    self.status_updated.emit(
                        f"下載失敗，{RETRY_DELAY} 秒後重試..."
                    )
                    for _ in range(RETRY_DELAY * 10):
                        if self._canceled:
                            self.download_canceled.emit()
                            return
                        time.sleep(0.1)
                else:
                    self.download_failed.emit(str(e))
                    return
            except Exception as e:
                self.download_failed.emit(str(e))
                return
