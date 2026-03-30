"""任務清單表格元件。"""

from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

from app.core.task_manager import TaskItem, TaskStatus

# 欄位定義
COLUMNS = ["檔案名稱", "類型", "長度", "狀態", "裝置", "模型", "輸出路徑"]

_STATUS_TEXT = {
    TaskStatus.PENDING: "等待中",
    TaskStatus.EXTRACTING: "抽取音軌中",
    TaskStatus.RUNNING: "轉錄中",
    TaskStatus.SUCCESS: "完成",
    TaskStatus.FAILED: "失敗",
    TaskStatus.CANCELED: "已取消",
}


class TaskTable(QTableWidget):
    """任務清單表格。"""

    def __init__(self, parent=None):
        super().__init__(0, len(COLUMNS), parent)
        self.setHorizontalHeaderLabels(COLUMNS)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

    def add_task_row(self, task: TaskItem) -> None:
        """新增一筆任務到表格。"""
        row = self.rowCount()
        self.insertRow(row)
        self.setItem(row, 0, QTableWidgetItem(task.file_name))
        self.setItem(row, 1, QTableWidgetItem(task.file_type))
        self.setItem(row, 2, QTableWidgetItem(f"{task.duration:.1f}s" if task.duration else "—"))
        self.setItem(row, 3, QTableWidgetItem(_STATUS_TEXT.get(task.status, "")))
        self.setItem(row, 4, QTableWidgetItem(task.device))
        self.setItem(row, 5, QTableWidgetItem(task.model))
        self.setItem(row, 6, QTableWidgetItem(task.output_dir))

    def update_task_row(self, row: int, task: TaskItem) -> None:
        """更新指定列的任務狀態。"""
        if 0 <= row < self.rowCount():
            self.setItem(row, 2, QTableWidgetItem(f"{task.duration:.1f}s" if task.duration else "—"))
            self.setItem(row, 3, QTableWidgetItem(_STATUS_TEXT.get(task.status, "")))
            self.setItem(row, 4, QTableWidgetItem(task.device))
            self.setItem(row, 5, QTableWidgetItem(task.model))
            self.setItem(row, 6, QTableWidgetItem(task.output_dir))

    def clear_all(self) -> None:
        """清空表格。"""
        self.setRowCount(0)
