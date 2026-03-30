"""模型管理模組 - 模型註冊、檢查、切換、載入。"""

import logging
import os
import shutil
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.utils import json_utils, paths

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """模型資訊。"""

    key: str
    label: str
    hf_repo: str
    local_dir: str
    enabled: bool
    is_downloaded: bool = False
    resolved_path: str = ""


def _has_model_files(path: str) -> bool:
    """檢查目錄是否包含模型檔案。"""
    if not os.path.isdir(path):
        return False
    files = os.listdir(path)
    return any(f.endswith((".bin", ".safetensors", ".pt", "config.json")) for f in files)


def _resolve_hf_cache(hf_repo: str) -> Optional[str]:
    """嘗試從 HuggingFace cache 解析 snapshot 路徑。"""
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
    return None


class ModelManager:
    """模型管理器。"""

    def __init__(self):
        self._registry: Dict = {}
        self._default_model: str = ""
        self.load_registry()

    def load_registry(self) -> None:
        """載入 model_registry.json。"""
        self._registry = json_utils.load_json(paths.get_model_registry_path(), {})
        self._default_model = self._registry.get("default_model", "breeze_asr_25")

    def _build_model_info(self, key: str, data: dict) -> ModelInfo:
        """從 registry dict 建構 ModelInfo 並偵測下載狀態。"""
        info = ModelInfo(
            key=key,
            label=data.get("label", key),
            hf_repo=data.get("hf_repo", ""),
            local_dir=data.get("local_dir", ""),
            enabled=data.get("enabled", False),
        )
        resolved = self._resolve_path(info)
        if resolved:
            info.is_downloaded = True
            info.resolved_path = resolved
        return info

    def _resolve_path(self, info: ModelInfo) -> Optional[str]:
        """解析模型本地路徑（local_dir 或 HF cache）。"""
        if info.local_dir:
            abs_local = os.path.join(paths.get_base_dir(), info.local_dir)
            if _has_model_files(abs_local):
                return abs_local
        if info.hf_repo:
            cached = _resolve_hf_cache(info.hf_repo)
            if cached:
                return cached
        return None

    def get_default_model_key(self) -> str:
        """取得預設模型 key。"""
        config = json_utils.load_json(paths.get_config_path(), {})
        return config.get("default_model", self._default_model)

    def get_default_model(self) -> Optional[ModelInfo]:
        """取得預設模型資訊。"""
        key = self.get_default_model_key()
        models = self._registry.get("models", {})
        data = models.get(key)
        if data is None:
            return None
        return self._build_model_info(key, data)

    def get_all_models(self) -> List[ModelInfo]:
        """取得所有已註冊模型。"""
        result: List[ModelInfo] = []
        for key, data in self._registry.get("models", {}).items():
            result.append(self._build_model_info(key, data))
        return result

    def get_model_path(self, model_key: str) -> Optional[str]:
        """取得模型本地路徑（若已下載）。"""
        models = self._registry.get("models", {})
        data = models.get(model_key)
        if data is None:
            return None
        info = self._build_model_info(model_key, data)
        return info.resolved_path if info.is_downloaded else None

    def set_default_model(self, model_key: str) -> None:
        """切換預設模型（寫入 config.json）。"""
        config = json_utils.load_json(paths.get_config_path(), {})
        config["default_model"] = model_key
        json_utils.save_json(paths.get_config_path(), config)
        logger.info("預設模型已切換為: %s", model_key)

    def delete_local_model(self, model_key: str) -> bool:
        """刪除模型本地檔案（僅限 runtime/models 內的）。"""
        models = self._registry.get("models", {})
        data = models.get(model_key)
        if data is None:
            return False
        local_dir = data.get("local_dir", "")
        if not local_dir:
            return False
        abs_local = os.path.join(paths.get_base_dir(), local_dir)
        if not abs_local.startswith(paths.get_models_dir()):
            logger.warning("拒絕刪除非 models 目錄內的路徑: %s", abs_local)
            return False
        if os.path.isdir(abs_local):
            shutil.rmtree(abs_local)
            logger.info("已刪除模型: %s (%s)", model_key, abs_local)
            return True
        return False

    def get_local_dir_abs(self, model_key: str) -> str:
        """取得模型的絕對 local_dir 路徑。"""
        models = self._registry.get("models", {})
        data = models.get(model_key, {})
        local_dir = data.get("local_dir", f"runtime/models/{model_key}")
        return os.path.join(paths.get_base_dir(), local_dir)

    def is_model_downloaded(self, model_key: str) -> bool:
        """檢查模型是否已存在。"""
        raise NotImplementedError("Phase 3 實作")
