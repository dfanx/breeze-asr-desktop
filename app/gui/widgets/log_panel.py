"""即時 Log 面板元件。"""

from PySide6.QtWidgets import QPlainTextEdit


class LogPanel(QPlainTextEdit):
    """顯示即時 log 的面板。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(1000)
        self.setPlaceholderText("日誌輸出…")

    def append_log(self, message: str) -> None:
        """新增一行 log。"""
        self.appendPlainText(message)
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def clear_log(self) -> None:
        """清除所有 log。"""
        self.clear()
