"""主視窗模組 - Breeze ASR Desktop 主介面。"""

import logging
import os

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.core.audio_loader import load_audio
from app.core.audio_segmenter import split_audio
from app.core.device_manager import DeviceInfo, get_device_info
from app.core.dictionary_manager import DictionaryManager
from app.core.exporter import export_full_txt, export_srt, export_txt
from app.core.task_manager import TaskItem, TaskManager, TaskStatus
from app.core.transcriber import Transcriber
from app.gui.widgets.file_drop_area import FileDropArea
from app.gui.widgets.log_panel import LogPanel
from app.gui.widgets.status_bar import StatusBar
from app.gui.widgets.task_table import TaskTable
from app.utils import json_utils, paths
from app.utils.file_utils import is_supported_audio

logger = logging.getLogger(__name__)


def _resolve_model_path(config: dict) -> str:
    """根據設定解析模型的本地路徑。"""
    registry = json_utils.load_json(paths.get_model_registry_path(), {})
    default_key = config.get("default_model", registry.get("default_model", "breeze_asr_25"))
    model_info = registry.get("models", {}).get(default_key, {})
    hf_repo = model_info.get("hf_repo", "MediaTek-Research/Breeze-ASR-25")
    local_dir = model_info.get("local_dir", "")

    # 1) 檢查 registry 指定的 local_dir（相對於 base_dir）
    if local_dir:
        abs_local = os.path.join(paths.get_base_dir(), local_dir)
        if os.path.isdir(abs_local) and _has_model_files(abs_local):
            return abs_local

    # 2) 檢查 HuggingFace cache（使用 huggingface_hub 解析 snapshot）
    try:
        from huggingface_hub import scan_cache_dir
        cache_info = scan_cache_dir()
        for repo_info in cache_info.repos:
            if repo_info.repo_id == hf_repo:
                for revision in repo_info.revisions:
                    snap = str(revision.snapshot_path)
                    if _has_model_files(snap):
                        return snap
    except Exception:
        pass

    # 3) 直接用 repo ID（會觸發下載或報錯）
    return hf_repo


def _has_model_files(path: str) -> bool:
    """檢查目錄是否包含模型檔案。"""
    if not os.path.isdir(path):
        return False
    files = os.listdir(path)
    return any(f.endswith((".bin", ".safetensors", ".pt", "config.json")) for f in files)


# ── 背景轉錄 Worker ──────────────────────────────────────────────


class TranscriptionWorker(QThread):
    """背景轉錄 Worker，避免 GUI 凍結。"""

    task_started = Signal(int)  # task index
    task_finished = Signal(int, object)  # (index, TaskItem)
    segment_progress = Signal(int, int, int)  # (task_index, current_seg, total_seg)
    all_finished = Signal()
    error_occurred = Signal(int, str)  # (index, error_msg)

    def __init__(
        self,
        task_manager: TaskManager,
        transcriber: Transcriber,
        device_info: DeviceInfo,
        model_path: str,
        config: dict,
        parent=None,
    ):
        super().__init__(parent)
        self._task_manager = task_manager
        self._transcriber = transcriber
        self._device_info = device_info
        self._model_path = model_path
        self._config = config

    def run(self):
        # 載入模型（若尚未載入）
        try:
            self._transcriber.load_model(self._model_path, self._device_info)
        except Exception as e:
            logger.error("模型載入失敗: %s", e)
            self.error_occurred.emit(-1, f"模型載入失敗: {e}")
            self.all_finished.emit()
            return

        segment_seconds = self._config.get("segment_seconds", 30)
        output_dir = self._config.get("output_dir", paths.get_output_dir())
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(paths.get_base_dir(), output_dir)
        os.makedirs(output_dir, exist_ok=True)

        continue_on_error = self._config.get("continue_on_error", True)
        export_flags = {
            "txt": self._config.get("export_txt", True),
            "full": self._config.get("export_full_txt", True),
            "srt": self._config.get("export_srt", True),
        }

        # 讀取字典 prompt
        dm = DictionaryManager()
        prompt = dm.get_prompt()

        pending = self._task_manager.get_pending_tasks()

        for idx, (task_index, task) in enumerate(pending):
            if self._task_manager.is_canceled:
                self._task_manager.update_task(task_index, status=TaskStatus.CANCELED)
                continue

            self.task_started.emit(task_index)
            self._task_manager.update_task(
                task_index,
                status=TaskStatus.RUNNING,
                device=self._device_info.device_name,
                model=os.path.basename(self._model_path),
                output_dir=output_dir,
            )

            try:
                # 載入音檔
                waveform, sr = load_audio(task.file_path)
                duration = len(waveform) / sr
                self._task_manager.update_task(task_index, duration=duration)

                # 切段
                segments = split_audio(waveform, sr, segment_seconds)

                # 轉錄
                def progress_cb(cur, tot, ti=task_index):
                    self.segment_progress.emit(ti, cur, tot)

                result = self._transcriber.transcribe_segments(
                    segments, sample_rate=sr, prompt=prompt, progress_callback=progress_cb
                )

                # 匯出
                base_name = os.path.splitext(task.file_name)[0]
                if export_flags["txt"]:
                    export_txt(result, os.path.join(output_dir, f"{base_name}.txt"))
                if export_flags["full"]:
                    export_full_txt(result, os.path.join(output_dir, f"{base_name}_full.txt"))
                if export_flags["srt"]:
                    export_srt(result, os.path.join(output_dir, f"{base_name}.srt"))

                self._task_manager.update_task(task_index, status=TaskStatus.SUCCESS)
                self.task_finished.emit(task_index, self._task_manager.tasks[task_index])

            except Exception as e:
                err_msg = str(e)
                logger.error("任務失敗 [%s]: %s", task.file_name, err_msg)
                self._task_manager.update_task(
                    task_index, status=TaskStatus.FAILED, error_message=err_msg
                )
                self.error_occurred.emit(task_index, err_msg)
                if not continue_on_error:
                    break

        self.all_finished.emit()


# ── 主視窗 ────────────────────────────────────────────────────────


class MainWindow(QMainWindow):
    """Breeze ASR Desktop 主視窗。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Breeze ASR Desktop")
        self.setMinimumSize(960, 640)

        self._task_manager = TaskManager(self)
        self._transcriber = Transcriber()
        self._dictionary_manager = DictionaryManager()
        self._worker: TranscriptionWorker | None = None
        self._config = self._load_config()
        self._device_info = get_device_info(self._config.get("prefer_gpu", True))

        self._init_ui()
        self._connect_signals()
        self._update_status_bar()

    def _load_config(self) -> dict:
        """載入設定（runtime > default fallback）。"""
        config = json_utils.load_json(paths.get_config_path(), None)
        if config is None:
            config = json_utils.load_json(paths.get_default_config_path(), {})
            json_utils.save_json(paths.get_config_path(), config)
        return config

    def _init_ui(self):
        """建立 UI 版面配置。"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # --- 上方區域：拖放 + 任務表 + 控制按鈕 ---
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左側：拖放區域
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        self._drop_area = FileDropArea()
        left_layout.addWidget(self._drop_area)

        # 加入檔案/資料夾按鈕
        btn_layout = QHBoxLayout()
        self._btn_add_file = QPushButton("加入檔案")
        self._btn_add_folder = QPushButton("加入資料夾")
        btn_layout.addWidget(self._btn_add_file)
        btn_layout.addWidget(self._btn_add_folder)
        left_layout.addLayout(btn_layout)
        left_panel.setMaximumWidth(280)

        # 中央：任務表格
        self._task_table = TaskTable()

        # 右側：控制區
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self._btn_start = QPushButton("開始轉錄")
        self._btn_stop = QPushButton("停止")
        self._btn_stop.setEnabled(False)
        self._btn_clear = QPushButton("清空清單")
        self._btn_open_output = QPushButton("開啟輸出資料夾")
        self._btn_settings = QPushButton("設定")
        self._btn_model_mgr = QPushButton("模型管理")
        self._btn_dictionary = QPushButton("字典")
        right_layout.addWidget(self._btn_start)
        right_layout.addWidget(self._btn_stop)
        right_layout.addWidget(self._btn_clear)
        right_layout.addWidget(self._btn_open_output)
        right_layout.addStretch()
        right_layout.addWidget(self._btn_settings)
        right_layout.addWidget(self._btn_model_mgr)
        right_layout.addWidget(self._btn_dictionary)
        right_panel.setMaximumWidth(160)

        splitter.addWidget(left_panel)
        splitter.addWidget(self._task_table)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        main_layout.addWidget(splitter, stretch=3)

        # --- 下方區域：Log 面板 ---
        self._log_panel = LogPanel()
        self._log_panel.setMaximumHeight(180)
        main_layout.addWidget(self._log_panel, stretch=1)

        # --- 最底部：狀態列 ---
        self._status_bar = StatusBar()
        main_layout.addWidget(self._status_bar)

    def _connect_signals(self):
        """連接按鈕與 task_manager 信號。"""
        self._btn_add_file.clicked.connect(self._on_add_file)
        self._btn_add_folder.clicked.connect(self._on_add_folder)
        self._btn_start.clicked.connect(self._on_start)
        self._btn_stop.clicked.connect(self._on_stop)
        self._btn_clear.clicked.connect(self._on_clear)
        self._btn_open_output.clicked.connect(self._on_open_output)
        self._btn_settings.clicked.connect(self._on_settings)
        self._btn_model_mgr.clicked.connect(self._on_model_manager)
        self._btn_dictionary.clicked.connect(self._on_dictionary)
        self._drop_area.files_dropped.connect(self._on_files_dropped)

        # task_manager signals → UI 更新
        self._task_manager.task_added.connect(self._on_task_added)
        self._task_manager.task_updated.connect(self._on_task_updated)
        self._task_manager.tasks_cleared.connect(self._task_table.clear_all)

    def _update_status_bar(self):
        """更新狀態列資訊。"""
        self._status_bar.set_device(self._device_info.device_name)
        if self._device_info.fallback_reason:
            self._status_bar.set_device(
                f"CPU（{self._device_info.fallback_reason}）"
            )

        registry = json_utils.load_json(paths.get_model_registry_path(), {})
        default_key = self._config.get(
            "default_model", registry.get("default_model", "breeze_asr_25")
        )
        model_info = registry.get("models", {}).get(default_key, {})
        self._status_bar.set_model(model_info.get("label", default_key))
        self._status_bar.set_task_count(0, self._task_manager.task_count)

    # ── Slots ──

    def _on_add_file(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "選擇音檔", "", "音檔 (*.mp3 *.wav)"
        )
        if files:
            self._on_files_dropped(files)

    def _on_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "選擇資料夾")
        if folder:
            self._on_files_dropped([folder])

    def _on_files_dropped(self, dropped_paths: list):
        for p in dropped_paths:
            if os.path.isdir(p):
                recursive = self._config.get("scan_subfolders", False)
                self._task_manager.add_tasks_from_folder(p, recursive=recursive)
            elif is_supported_audio(p):
                self._task_manager.add_task(p)
        self._status_bar.set_task_count(0, self._task_manager.task_count)

    def _on_task_added(self, task: TaskItem):
        self._task_table.add_task_row(task)

    def _on_task_updated(self, index: int, task: TaskItem):
        self._task_table.update_task_row(index, task)

    def _on_start(self):
        pending = self._task_manager.get_pending_tasks()
        if not pending:
            QMessageBox.information(self, "提示", "沒有待處理的任務。")
            return

        model_path = _resolve_model_path(self._config)
        logger.info("使用模型路徑: %s", model_path)

        self._task_manager.reset_cancel()
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._status_bar.set_progress_range(0, len(pending))
        self._status_bar.set_progress(0)

        self._worker = TranscriptionWorker(
            task_manager=self._task_manager,
            transcriber=self._transcriber,
            device_info=self._device_info,
            model_path=model_path,
            config=self._config,
            parent=self,
        )
        self._worker.task_started.connect(self._on_worker_task_started)
        self._worker.task_finished.connect(self._on_worker_task_finished)
        self._worker.segment_progress.connect(self._on_worker_segment_progress)
        self._worker.error_occurred.connect(self._on_worker_error)
        self._worker.all_finished.connect(self._on_worker_all_finished)
        self._worker.start()

    def _on_stop(self):
        if self._worker and self._worker.isRunning():
            self._task_manager.cancel()
            logger.info("已發送停止請求")

    def _on_clear(self):
        self._task_manager.clear_tasks()
        self._status_bar.set_task_count(0, 0)
        self._status_bar.set_progress(0)

    def _on_open_output(self):
        output = self._config.get("output_dir", paths.get_output_dir())
        if not os.path.isabs(output):
            output = os.path.join(paths.get_base_dir(), output)
        os.makedirs(output, exist_ok=True)
        os.startfile(output)

    def _on_settings(self):
        from app.gui.settings_dialog import SettingsDialog

        dlg = SettingsDialog(self)
        if dlg.exec():
            self._config = dlg.config
            self._device_info = get_device_info(self._config.get("prefer_gpu", True))
            self._update_status_bar()
            logger.info("設定已更新")

    def _on_model_manager(self):
        from app.gui.model_manager_dialog import ModelManagerDialog

        dlg = ModelManagerDialog(self)
        dlg.exec()
        self._update_status_bar()

    def _on_dictionary(self):
        from app.gui.dictionary_dialog import DictionaryDialog

        dlg = DictionaryDialog(self, dictionary_manager=self._dictionary_manager)
        dlg.exec()

    # ── Worker callback slots ──

    def _on_worker_task_started(self, index: int):
        completed = sum(
            1 for t in self._task_manager.tasks
            if t.status in (TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELED)
        )
        self._status_bar.set_task_count(completed, self._task_manager.task_count)

    def _on_worker_task_finished(self, index: int, task: TaskItem):
        completed = sum(
            1 for t in self._task_manager.tasks
            if t.status in (TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELED)
        )
        self._status_bar.set_task_count(completed, self._task_manager.task_count)
        self._status_bar.set_progress(completed)

    def _on_worker_segment_progress(self, task_index: int, cur: int, total: int):
        logger.debug("任務 %d: 片段 %d/%d", task_index, cur, total)

    def _on_worker_error(self, index: int, msg: str):
        if index == -1:
            QMessageBox.critical(self, "錯誤", msg)

    def _on_worker_all_finished(self):
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._worker = None
        completed = sum(
            1 for t in self._task_manager.tasks
            if t.status == TaskStatus.SUCCESS
        )
        failed = sum(
            1 for t in self._task_manager.tasks
            if t.status == TaskStatus.FAILED
        )
        logger.info("批次轉錄完成: %d 成功, %d 失敗", completed, failed)
        self._status_bar.set_task_count(
            completed + failed, self._task_manager.task_count
        )
