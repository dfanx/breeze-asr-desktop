"""任務管理模組 - 管理轉錄任務佇列與狀態流轉。"""

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import List

from PySide6.QtCore import QObject, Signal

from app.utils.file_utils import is_supported_audio, scan_audio_files

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任務狀態。"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class TaskItem:
    """單一任務項目。"""

    file_path: str
    file_name: str = ""
    file_type: str = ""
    duration: float = 0.0
    status: TaskStatus = TaskStatus.PENDING
    device: str = ""
    model: str = ""
    output_dir: str = ""
    error_message: str = ""

    def __post_init__(self):
        if not self.file_name:
            self.file_name = os.path.basename(self.file_path)
        if not self.file_type:
            _, ext = os.path.splitext(self.file_path)
            self.file_type = ext.lstrip(".").upper()


class TaskManager(QObject):
    """任務佇列管理器。"""

    task_added = Signal(object)  # TaskItem
    task_updated = Signal(int, object)  # (index, TaskItem)
    tasks_cleared = Signal()
    batch_started = Signal()
    batch_finished = Signal()
    progress_updated = Signal(int, int)  # current, total

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tasks: List[TaskItem] = []
        self._canceled = False

    @property
    def tasks(self) -> List[TaskItem]:
        return list(self._tasks)

    @property
    def task_count(self) -> int:
        return len(self._tasks)

    def add_task(self, file_path: str) -> TaskItem:
        """加入單一任務。"""
        task = TaskItem(file_path=file_path)
        self._tasks.append(task)
        self.task_added.emit(task)
        logger.info("已加入任務: %s", task.file_name)
        return task

    def add_tasks_from_folder(self, folder: str, recursive: bool = False) -> List[TaskItem]:
        """從資料夾掃描並加入所有音檔任務。"""
        files = scan_audio_files(folder, recursive=recursive)
        added = []
        for f in files:
            added.append(self.add_task(f))
        logger.info("從資料夾加入 %d 個任務: %s", len(added), folder)
        return added

    def clear_tasks(self) -> None:
        """清空所有任務。"""
        self._tasks.clear()
        self.tasks_cleared.emit()
        logger.info("任務清單已清空")

    def update_task(self, index: int, **kwargs) -> None:
        """更新指定索引的任務欄位。"""
        if 0 <= index < len(self._tasks):
            task = self._tasks[index]
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            self.task_updated.emit(index, task)

    def get_pending_tasks(self) -> List[tuple[int, TaskItem]]:
        """取得所有待處理的任務 (index, task)。"""
        return [
            (i, t) for i, t in enumerate(self._tasks)
            if t.status == TaskStatus.PENDING
        ]

    def cancel(self) -> None:
        """設定取消旗標。"""
        self._canceled = True
        logger.info("已請求取消批次轉錄")

    def reset_cancel(self) -> None:
        """重設取消旗標。"""
        self._canceled = False

    @property
    def is_canceled(self) -> bool:
        return self._canceled
