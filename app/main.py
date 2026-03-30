"""Breeze ASR Desktop - 程式入口。"""

import sys
import logging

from PySide6.QtWidgets import QApplication

from app.core.logger import setup_logging, set_gui_callback
from app.utils.paths import ensure_runtime_dirs


def main():
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

    # 建立主視窗
    from app.gui.main_window import MainWindow

    window = MainWindow()

    # 連接 log callback 到主視窗 log 面板
    set_gui_callback(window._log_panel.append_log)

    window.show()
    logging.info("Breeze ASR Desktop 已啟動")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
