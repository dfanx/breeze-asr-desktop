"""字典管理模組 - 讀寫 Dictionary.txt 並產生 prompt。"""

import logging
import os
from typing import List

from app.utils.paths import get_dictionary_path

logger = logging.getLogger(__name__)


class DictionaryManager:
    """字典管理器。"""

    def __init__(self, dict_path: str | None = None):
        self._path = dict_path or get_dictionary_path()
        self._words: List[str] = []

    @property
    def path(self) -> str:
        return self._path

    @property
    def words(self) -> List[str]:
        return list(self._words)

    def load(self) -> List[str]:
        """讀取字典檔案，回傳清洗後的字詞列表。"""
        self._words = []
        if not os.path.isfile(self._path):
            logger.info("字典檔案不存在: %s", self._path)
            return self._words
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    word = line.strip()
                    if word:
                        self._words.append(word)
            logger.info("已載入 %d 個字詞", len(self._words))
        except OSError as e:
            logger.error("讀取字典失敗: %s", e)
        return list(self._words)

    def save(self, words: List[str]) -> None:
        """將字詞列表寫入字典檔案。"""
        self._words = [w.strip() for w in words if w.strip()]
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            for word in self._words:
                f.write(word + "\n")
        logger.info("已儲存 %d 個字詞到 %s", len(self._words), self._path)

    def get_prompt(self) -> str:
        """將字詞合併為 prompt 字串供 Whisper 使用。"""
        if not self._words:
            self.load()
        return " ".join(self._words) if self._words else ""

    def import_from_file(self, file_path: str) -> List[str]:
        """從外部 txt 匯入字詞。"""
        words: List[str] = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                word = line.strip()
                if word:
                    words.append(word)
        self._words = words
        self.save(self._words)
        return list(self._words)

    def export_to_file(self, file_path: str) -> None:
        """將字詞匯出到外部 txt。"""
        with open(file_path, "w", encoding="utf-8") as f:
            for word in self._words:
                f.write(word + "\n")
        logger.info("已匯出字典到 %s", file_path)
