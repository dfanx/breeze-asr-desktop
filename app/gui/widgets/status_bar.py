"""底部狀態列元件。"""

from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QWidget


class StatusBar(QWidget):
    """底部狀態列 - 顯示模型狀態、裝置狀態、任務數、進度。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        self._model_label = QLabel("模型: 未載入")
        self._device_label = QLabel("裝置: —")
        self._task_label = QLabel("任務: 0/0")
        self._progress = QProgressBar()
        self._progress.setMaximumWidth(200)
        self._progress.setValue(0)

        layout.addWidget(self._model_label)
        layout.addWidget(self._device_label)
        layout.addStretch()
        layout.addWidget(self._task_label)
        layout.addWidget(self._progress)

    def set_model(self, name: str) -> None:
        self._model_label.setText(f"模型: {name}")

    def set_device(self, name: str) -> None:
        self._device_label.setText(f"裝置: {name}")

    def set_task_count(self, current: int, total: int) -> None:
        self._task_label.setText(f"任務: {current}/{total}")

    def set_progress(self, value: int) -> None:
        self._progress.setValue(value)

    def set_progress_range(self, minimum: int, maximum: int) -> None:
        self._progress.setRange(minimum, maximum)
