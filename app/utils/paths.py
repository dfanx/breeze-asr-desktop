"""路徑管理模組 - 集中管理所有路徑，支援 PyInstaller 打包環境。"""

import os
import sys


def get_base_dir() -> str:
    """取得程式根目錄（支援 PyInstaller 打包環境）。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_runtime_dir() -> str:
    """取得 runtime 目錄路徑。"""
    return os.path.join(get_base_dir(), "runtime")


def get_output_dir() -> str:
    """取得預設輸出目錄路徑。"""
    return os.path.join(get_runtime_dir(), "output")


def get_logs_dir() -> str:
    """取得 log 目錄路徑。"""
    return os.path.join(get_runtime_dir(), "logs")


def get_models_dir() -> str:
    """取得模型目錄路徑。"""
    return os.path.join(get_runtime_dir(), "models")


def get_config_path() -> str:
    """取得 runtime config.json 路徑。"""
    return os.path.join(get_runtime_dir(), "config.json")


def get_default_config_path() -> str:
    """取得內建預設 default_config.json 路徑。"""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "app", "config", "default_config.json")
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config",
        "default_config.json",
    )


def get_model_registry_path() -> str:
    """取得內建 model_registry.json 路徑。"""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "app", "config", "model_registry.json")
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config",
        "model_registry.json",
    )


def get_dictionary_path() -> str:
    """取得 Dictionary.txt 路徑。"""
    return os.path.join(get_runtime_dir(), "Dictionary.txt")


def ensure_runtime_dirs():
    """確保所有 runtime 子目錄存在。"""
    for d in [get_runtime_dir(), get_output_dir(), get_logs_dir(), get_models_dir()]:
        os.makedirs(d, exist_ok=True)
