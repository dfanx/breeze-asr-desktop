"""字典編輯對話框 - 編輯 Dictionary.txt。"""

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from app.core.dictionary_manager import DictionaryManager


class DictionaryDialog(QDialog):
    """字典編輯對話框。"""

    def __init__(self, parent=None, dictionary_manager: DictionaryManager | None = None):
        super().__init__(parent)
        self.setWindowTitle("字典編輯")
        self.setMinimumSize(480, 400)
        self._dm = dictionary_manager or DictionaryManager()
        self._init_ui()
        self._load_words()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("每行一個字詞或片語，用來提高專有名詞辨識準確度："))

        self._editor = QPlainTextEdit()
        self._editor.setPlaceholderText("例如:\nBreeze ASR\n聯發科技\nMediaTek")
        layout.addWidget(self._editor)

        # 匯入/匯出按鈕
        io_layout = QHBoxLayout()
        self._btn_import = QPushButton("匯入 TXT")
        self._btn_export = QPushButton("匯出 TXT")
        self._btn_reset = QPushButton("重設")
        io_layout.addWidget(self._btn_import)
        io_layout.addWidget(self._btn_export)
        io_layout.addStretch()
        io_layout.addWidget(self._btn_reset)
        layout.addLayout(io_layout)

        self._btn_import.clicked.connect(self._on_import)
        self._btn_export.clicked.connect(self._on_export)
        self._btn_reset.clicked.connect(self._load_words)

        # 確定/取消
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_words(self):
        words = self._dm.load()
        self._editor.setPlainText("\n".join(words))

    def _save_and_accept(self):
        text = self._editor.toPlainText()
        words = [line.strip() for line in text.splitlines() if line.strip()]
        self._dm.save(words)
        self.accept()

    def _on_import(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "匯入字典", "", "文字檔 (*.txt)"
        )
        if file_path:
            try:
                words = self._dm.import_from_file(file_path)
                self._editor.setPlainText("\n".join(words))
            except Exception as e:
                QMessageBox.warning(self, "匯入失敗", str(e))

    def _on_export(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "匯出字典", "Dictionary.txt", "文字檔 (*.txt)"
        )
        if file_path:
            try:
                text = self._editor.toPlainText()
                words = [line.strip() for line in text.splitlines() if line.strip()]
                self._dm.save(words)
                self._dm.export_to_file(file_path)
            except Exception as e:
                QMessageBox.warning(self, "匯出失敗", str(e))
