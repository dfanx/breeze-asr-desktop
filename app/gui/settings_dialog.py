"""設定對話框 - 編輯應用程式設定。"""

import os

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from app.utils import json_utils, paths


class SettingsDialog(QDialog):
    """設定對話框。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("設定")
        self.setMinimumSize(480, 360)
        self._config = json_utils.load_json(paths.get_config_path(), {})
        self._init_ui()
        self._load_values()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        # 輸出資料夾
        output_row = QHBoxLayout()
        self._output_edit = QLineEdit()
        self._output_browse = QPushButton("瀏覽…")
        self._output_browse.clicked.connect(self._browse_output)
        output_row.addWidget(self._output_edit)
        output_row.addWidget(self._output_browse)
        form.addRow("輸出資料夾:", output_row)

        # 切段秒數
        self._segment_spin = QSpinBox()
        self._segment_spin.setRange(10, 120)
        self._segment_spin.setSuffix(" 秒")
        form.addRow("切段長度:", self._segment_spin)

        # GPU 優先
        self._gpu_check = QCheckBox("優先使用 GPU")
        form.addRow("", self._gpu_check)

        # 失敗繼續
        self._continue_check = QCheckBox("批次轉錄中遇到錯誤繼續處理")
        form.addRow("", self._continue_check)

        # 遞迴掃描
        self._recursive_check = QCheckBox("掃描子資料夾")
        form.addRow("", self._recursive_check)

        # 保留暫存音檔
        self._keep_temp_check = QCheckBox("保留影片抽取的暫存音檔")
        form.addRow("", self._keep_temp_check)

        # 輸出格式
        self._txt_check = QCheckBox("輸出 .txt")
        self._full_check = QCheckBox("輸出 _full.txt")
        self._srt_check = QCheckBox("輸出 .srt")
        form.addRow("輸出格式:", self._txt_check)
        form.addRow("", self._full_check)
        form.addRow("", self._srt_check)

        layout.addLayout(form)
        layout.addStretch()

        # 按鈕
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_values(self):
        self._output_edit.setText(
            self._config.get("output_dir", "runtime/output")
        )
        self._segment_spin.setValue(self._config.get("segment_seconds", 30))
        self._gpu_check.setChecked(self._config.get("prefer_gpu", True))
        self._continue_check.setChecked(self._config.get("continue_on_error", True))
        self._recursive_check.setChecked(self._config.get("scan_subfolders", False))
        self._keep_temp_check.setChecked(self._config.get("keep_temp_audio", False))
        self._txt_check.setChecked(self._config.get("export_txt", True))
        self._full_check.setChecked(self._config.get("export_full_txt", True))
        self._srt_check.setChecked(self._config.get("export_srt", True))

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "選擇輸出資料夾")
        if folder:
            self._output_edit.setText(folder)

    def _save_and_accept(self):
        self._config["output_dir"] = self._output_edit.text()
        self._config["segment_seconds"] = self._segment_spin.value()
        self._config["prefer_gpu"] = self._gpu_check.isChecked()
        self._config["continue_on_error"] = self._continue_check.isChecked()
        self._config["scan_subfolders"] = self._recursive_check.isChecked()
        self._config["keep_temp_audio"] = self._keep_temp_check.isChecked()
        self._config["export_txt"] = self._txt_check.isChecked()
        self._config["export_full_txt"] = self._full_check.isChecked()
        self._config["export_srt"] = self._srt_check.isChecked()
        json_utils.save_json(paths.get_config_path(), self._config)
        self.accept()

    @property
    def config(self) -> dict:
        return dict(self._config)
