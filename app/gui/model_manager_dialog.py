"""模型管理對話框 - 管理已註冊模型。"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.core.downloader import DownloadWorker
from app.core.model_manager import ModelManager

logger = logging.getLogger(__name__)


class ModelManagerDialog(QDialog):
    """模型管理對話框。"""

    COLUMNS = ["模型名稱", "HuggingFace Repo", "狀態", "預設"]

    def __init__(self, parent=None, model_manager: ModelManager | None = None):
        super().__init__(parent)
        self.setWindowTitle("模型管理")
        self.setMinimumSize(620, 420)
        self._mm = model_manager or ModelManager()
        self._download_worker: DownloadWorker | None = None
        self._downloading_key: str = ""

        self._setup_ui()
        self._refresh_table()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 模型表格
        self._table = QTableWidget(0, len(self.COLUMNS))
        self._table.setHorizontalHeaderLabels(self.COLUMNS)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        layout.addWidget(self._table)

        # 進度區
        progress_layout = QHBoxLayout()
        self._progress_label = QLabel("")
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setVisible(False)
        progress_layout.addWidget(self._progress_label, 1)
        progress_layout.addWidget(self._progress_bar, 1)
        layout.addLayout(progress_layout)

        # 按鈕列
        btn_layout = QHBoxLayout()
        self._btn_download = QPushButton("下載")
        self._btn_set_default = QPushButton("設為預設")
        self._btn_delete = QPushButton("刪除本地檔案")
        self._btn_cancel_dl = QPushButton("取消下載")
        self._btn_cancel_dl.setEnabled(False)
        self._btn_close = QPushButton("關閉")

        btn_layout.addWidget(self._btn_download)
        btn_layout.addWidget(self._btn_set_default)
        btn_layout.addWidget(self._btn_delete)
        btn_layout.addWidget(self._btn_cancel_dl)
        btn_layout.addStretch()
        btn_layout.addWidget(self._btn_close)
        layout.addLayout(btn_layout)

        # 連接
        self._btn_download.clicked.connect(self._on_download)
        self._btn_set_default.clicked.connect(self._on_set_default)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_cancel_dl.clicked.connect(self._on_cancel_download)
        self._btn_close.clicked.connect(self.accept)

    def _refresh_table(self):
        self._mm.load_registry()
        models = self._mm.get_all_models()
        default_key = self._mm.get_default_model_key()
        self._table.setRowCount(len(models))

        for row, m in enumerate(models):
            self._table.setItem(row, 0, QTableWidgetItem(m.label))
            self._table.setItem(row, 1, QTableWidgetItem(m.hf_repo or "—"))

            status = "已下載" if m.is_downloaded else ("未下載" if m.hf_repo else "無 repo")
            status_item = QTableWidgetItem(status)
            self._table.setItem(row, 2, status_item)

            is_default = "★" if m.key == default_key else ""
            default_item = QTableWidgetItem(is_default)
            default_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 3, default_item)

            # 儲存 key 到 row data
            self._table.item(row, 0).setData(Qt.UserRole, m.key)

    def _selected_key(self) -> str | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _on_set_default(self):
        key = self._selected_key()
        if not key:
            QMessageBox.information(self, "提示", "請先選擇一個模型。")
            return
        self._mm.set_default_model(key)
        self._refresh_table()
        QMessageBox.information(self, "提示", "預設模型已切換，下次啟動轉錄時生效。")

    def _on_download(self):
        key = self._selected_key()
        if not key:
            QMessageBox.information(self, "提示", "請先選擇一個模型。")
            return
        if self._download_worker and self._download_worker.isRunning():
            QMessageBox.warning(self, "提示", "已有下載進行中，請先取消或等待完成。")
            return

        models = self._mm.get_all_models()
        info = next((m for m in models if m.key == key), None)
        if not info or not info.hf_repo:
            QMessageBox.warning(self, "錯誤", "此模型沒有設定 HuggingFace repo。")
            return
        if info.is_downloaded:
            ret = QMessageBox.question(
                self, "確認", f"模型 {info.label} 已存在，要重新下載嗎？"
            )
            if ret != QMessageBox.Yes:
                return

        local_dir = self._mm.get_local_dir_abs(key)
        self._downloading_key = key
        self._download_worker = DownloadWorker(info.hf_repo, local_dir, self)
        self._download_worker.progress_updated.connect(self._on_dl_progress)
        self._download_worker.status_updated.connect(self._on_dl_status)
        self._download_worker.download_finished.connect(self._on_dl_finished)
        self._download_worker.download_failed.connect(self._on_dl_failed)
        self._download_worker.download_canceled.connect(self._on_dl_canceled)

        self._btn_download.setEnabled(False)
        self._btn_cancel_dl.setEnabled(True)
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)
        self._download_worker.start()

    def _on_cancel_download(self):
        if self._download_worker and self._download_worker.isRunning():
            self._download_worker.cancel()

    def _on_dl_progress(self, ratio: float):
        self._progress_bar.setValue(int(ratio * 100))

    def _on_dl_status(self, text: str):
        self._progress_label.setText(text)

    def _on_dl_finished(self, local_path: str):
        self._reset_download_ui()
        self._progress_label.setText("下載完成")
        self._refresh_table()
        logger.info("模型下載完成: %s -> %s", self._downloading_key, local_path)

    def _on_dl_failed(self, error: str):
        self._reset_download_ui()
        self._progress_label.setText("下載失敗")
        QMessageBox.critical(self, "下載失敗", error)

    def _on_dl_canceled(self):
        self._reset_download_ui()
        self._progress_label.setText("已取消下載")

    def _reset_download_ui(self):
        self._btn_download.setEnabled(True)
        self._btn_cancel_dl.setEnabled(False)
        self._progress_bar.setVisible(False)
        self._downloading_key = ""

    def _on_delete(self):
        key = self._selected_key()
        if not key:
            QMessageBox.information(self, "提示", "請先選擇一個模型。")
            return
        models = self._mm.get_all_models()
        info = next((m for m in models if m.key == key), None)
        if not info or not info.is_downloaded:
            QMessageBox.information(self, "提示", "此模型尚未下載。")
            return

        ret = QMessageBox.question(
            self, "確認刪除", f"確定要刪除 {info.label} 的本地檔案嗎？"
        )
        if ret != QMessageBox.Yes:
            return

        if self._mm.delete_local_model(key):
            self._refresh_table()
            QMessageBox.information(self, "完成", "模型已刪除。")
        else:
            QMessageBox.warning(self, "錯誤", "無法刪除此模型（可能不在 models 目錄內）。")

    def closeEvent(self, event):
        if self._download_worker and self._download_worker.isRunning():
            ret = QMessageBox.question(
                self, "確認", "下載進行中，確定要關閉嗎？（下載將被取消）"
            )
            if ret != QMessageBox.Yes:
                event.ignore()
                return
            self._download_worker.cancel()
            self._download_worker.wait(3000)
        super().closeEvent(event)
