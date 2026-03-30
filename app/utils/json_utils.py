"""JSON 讀寫工具模組。"""

import json
import os
from typing import Any


def load_json(path: str, default: Any = None) -> Any:
    """讀取 JSON 檔案，若不存在或解析失敗則回傳 default。"""
    if not os.path.isfile(path):
        return default if default is not None else {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default if default is not None else {}


def save_json(path: str, data: Any) -> None:
    """將資料寫入 JSON 檔案（自動建立目錄）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
