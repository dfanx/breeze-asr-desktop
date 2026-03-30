"""Breeze ASR Desktop - 程式入口。"""

import os
import sys
import logging

from PySide6.QtWidgets import QApplication

from app.core.logger import setup_logging, set_gui_callback
from app.utils.paths import ensure_runtime_dirs


def _fix_std_streams():
    """在 PyInstaller windowed 模式下，sys.stdout/stderr 可能為 None，
    導致任何 print / logging 寫入時崩潰。重導到 devnull。"""
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")


def main():
    # 修正 windowed 模式下的 stdout/stderr
    _fix_std_streams()

    # 初始化 runtime 目錄
    ensure_runtime_dirs()

    # 初始化日誌
    setup_logging()

    # 全域例外攔截
    def exception_hook(exc_type, exc_value, exc_tb):
        logging.critical("未捕獲的例外", exc_info=(exc_type, exc_value, exc_tb))
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = exception_hook

    # 建立應用程式
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
