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
        try:
            self._run_download()
        except BaseException as e:
            # 捕捉所有例外（含 SystemExit、KeyboardInterrupt），
            # 防止背景執行緒的未捕獲例外導致整個程式崩潰。
            logger.critical("下載執行緒發生未預期的嚴重錯誤: %s", e, exc_info=True)
            try:
                self.download_failed.emit(f"下載過程發生嚴重錯誤: {e}")
            except Exception:
                pass

    def _run_download(self) -> None:
        """實際下載邏輯（從 run() 呼叫）。"""
        # 停用 hf_xet 原生傳輸，避免在 PyInstaller 打包環境中原生程式庫崩潰
        os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

        # 獨立處理 import，避免套件載入失敗直接崩潰
        try:
            from huggingface_hub import snapshot_download
            from huggingface_hub.utils import (
                HfHubHTTPError,
                LocalEntryNotFoundError,
            )
        except ImportError as e:
            logger.error("無法匯入 huggingface_hub: %s", e)
            self.download_failed.emit(
                f"缺少必要套件 huggingface_hub，請先安裝：\npip install huggingface_hub\n\n錯誤: {e}"
            )
            return

        os.makedirs(self._local_dir, exist_ok=True)
        logger.info("開始下載模型: repo=%s, local_dir=%s", self._hf_repo, self._local_dir)

        for attempt in range(1, MAX_RETRIES + 1):
            if self._canceled:
                self.download_canceled.emit()
                return

            try:
                self.status_updated.emit(
                    f"下載中（第 {attempt}/{MAX_RETRIES} 次嘗試）..."
                )
                self.progress_updated.emit(0.0)

                logger.info("snapshot_download 開始 (第 %d 次)", attempt)
                local_path = snapshot_download(
                    repo_id=self._hf_repo,
                    local_dir=self._local_dir,
                    resume_download=True,
                )
                logger.info("snapshot_download 完成: %s", local_path)

                if self._canceled:
                    self.download_canceled.emit()
                    return

                self.progress_updated.emit(1.0)
                self.status_updated.emit("下載完成")
                self.download_finished.emit(local_path)
                return

            except (HfHubHTTPError, LocalEntryNotFoundError, OSError) as e:
                logger.warning("下載失敗 (第 %d 次): %s", attempt, e, exc_info=True)
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
                logger.error("下載發生未預期錯誤: %s", e, exc_info=True)
                self.download_failed.emit(f"下載錯誤: {e}")
                return
