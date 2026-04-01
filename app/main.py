"""Breeze ASR Desktop - 程式入口。"""

import os
import sys
import logging
import threading

from app.utils.paths import ensure_runtime_dirs


def _fix_std_streams():
    """在 PyInstaller windowed 模式下，sys.stdout/stderr 可能為 None，
    導致任何 print / logging 寫入時崩潰。重導到 devnull。"""
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")


def _attach_console():
    """Windows 下 windowed exe 重新附著到父 console，使 print 有輸出。"""
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            ATTACH_PARENT_PROCESS = -1
            if kernel32.AttachConsole(ATTACH_PARENT_PROCESS):
                sys.stdout = open("CONOUT$", "w", encoding="utf-8")
                sys.stderr = open("CONOUT$", "w", encoding="utf-8")
        except Exception:
            pass


def _cli_download_model():
    """CLI 模式：直接在 console 下載模型，不啟動 GUI。"""
    _attach_console()
    ensure_runtime_dirs()

    from app.utils import json_utils, paths

    registry = json_utils.load_json(paths.get_model_registry_path(), {})
    default_key = registry.get("default_model", "breeze_asr_25")
    model_info = registry.get("models", {}).get(default_key, {})
    hf_repo = model_info.get("hf_repo", "MediaTek-Research/Breeze-ASR-25")
    local_dir = model_info.get("local_dir", f"runtime/models/{default_key}")
    abs_local = os.path.join(paths.get_base_dir(), local_dir)

    os.makedirs(abs_local, exist_ok=True)

    print(f"模型: {default_key}")
    print(f"HuggingFace Repo: {hf_repo}")
    print(f"下載目錄: {abs_local}")
    print("開始下載（視模型大小與網速，可能需要數分鐘）...\n")

    # 停用 hf_xet 以避免原生程式庫相容性問題
    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

    try:
        from huggingface_hub import snapshot_download

        local_path = snapshot_download(
            repo_id=hf_repo,
            local_dir=abs_local,
            resume_download=True,
        )
        print(f"\n下載完成！模型已儲存至: {local_path}")

    except Exception as e:
        print(f"\n下載失敗: {e}")
        input("按 Enter 鍵關閉...")
        sys.exit(1)


def main():
    # 檢查 CLI 模式：--download-model
    if "--download-model" in sys.argv:
        _cli_download_model()
        return

    # 修正 windowed 模式下的 stdout/stderr
    _fix_std_streams()

    # 初始化 runtime 目錄
    ensure_runtime_dirs()

    # 初始化日誌
    from app.core.logger import setup_logging, set_gui_callback
    setup_logging()

    # 全域例外攔截
    def exception_hook(exc_type, exc_value, exc_tb):
        logging.critical("未捕獲的例外", exc_info=(exc_type, exc_value, exc_tb))
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = exception_hook

    # 攔截背景執行緒中的未捕獲例外，防止程式靜默崩潰
    def threading_exception_hook(args):
        logging.critical(
            "執行緒 '%s' 發生未捕獲的例外: %s",
            args.thread.name if args.thread else "unknown",
            args.exc_value,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    threading.excepthook = threading_exception_hook

    # 建立應用程式
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("Breeze ASR Desktop")

    # 啟動畫面 — 讓使用者知道程式正在載入
    from PySide6.QtWidgets import QSplashScreen, QLabel
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPixmap, QColor, QPainter, QFont

    # 動態產生啟動畫面
    pixmap = QPixmap(480, 200)
    pixmap.fill(QColor(30, 30, 30))
    painter = QPainter(pixmap)
    painter.setPen(QColor(220, 220, 220))
    font = QFont("Microsoft JhengHei", 22, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "Breeze ASR Desktop\n載入中…")
    painter.end()

    splash = QSplashScreen(pixmap)
    splash.show()
    app.processEvents()

    # 建立主視窗（觸發重量級 import：torch、transformers 等）
    from app.gui.main_window import MainWindow

    window = MainWindow()

    # 連接 log callback 到主視窗 log 面板
    set_gui_callback(window._log_panel.append_log)

    splash.finish(window)
    window.show()
    logging.info("Breeze ASR Desktop 已啟動")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
