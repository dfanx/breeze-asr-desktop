"""拖放區域元件 - 支援拖曳音檔/資料夾。"""

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.utils.file_utils import is_supported_media


class FileDropArea(QWidget):
    """支援拖曳音檔/資料夾的 UI 區塊。"""

    files_dropped = Signal(list)  # List[str] — 拖入的檔案/資料夾路徑

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self._label = QLabel("將音檔/影片或資料夾拖曳到此處\n或點擊下方按鈕加入")
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setMinimumHeight(120)
        self._label.setStyleSheet(
            "border: 2px dashed #888; border-radius: 8px; padding: 20px; color: #888;"
        )
        layout.addWidget(self._label)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path) or is_supported_media(path):
                paths.append(path)
        if paths:
            self.files_dropped.emit(paths)
