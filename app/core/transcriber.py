"""轉錄核心模組 - 使用 WhisperProcessor + WhisperForConditionalGeneration 進行語音辨識。

不使用 pipeline，直接呼叫 model.generate()，避免 torchcodec 等不可控依賴。
"""

import gc
import logging
from dataclasses import dataclass

import numpy as np
import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor

from app.core.audio_segmenter import AudioSegment
from app.core.device_manager import DeviceInfo

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionSegment:
    """轉錄結果片段。"""

    start: float
    end: float
    text: str


@dataclass
class TranscriptionResult:
    """完整轉錄結果。"""

    full_text: str
    segments: list[TranscriptionSegment]


class Transcriber:
    """語音轉文字引擎。"""

    def __init__(self):
        self._processor: WhisperProcessor | None = None
        self._model: WhisperForConditionalGeneration | None = None
        self._device_info: DeviceInfo | None = None
        self._model_path: str | None = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None and self._processor is not None

    def load_model(self, model_path: str, device_info: DeviceInfo) -> None:
        """載入模型與 processor。

        Args:
            model_path: 模型本地路徑或 HuggingFace repo ID。
            device_info: 裝置資訊。
        """
        if self.is_loaded and self._model_path == model_path:
            logger.info("模型已載入，跳過: %s", model_path)
            return

        self.unload_model()
        logger.info("載入模型: %s (裝置: %s)", model_path, device_info.device)

        self._processor = WhisperProcessor.from_pretrained(model_path)
        self._model = WhisperForConditionalGeneration.from_pretrained(
            model_path, torch_dtype=device_info.dtype
        )
        self._model.to(device_info.device)
        self._model.eval()
        self._device_info = device_info
        self._model_path = model_path

        logger.info("模型載入完成")

    def unload_model(self) -> None:
        """釋放模型記憶體。"""
        if self._model is not None:
            del self._model
            self._model = None
        if self._processor is not None:
            del self._processor
            self._processor = None
        self._device_info = None
        self._model_path = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def transcribe_segments(
        self,
        segments: list[AudioSegment],
        sample_rate: int = 16000,
        prompt: str = "",
        language: str = "zh",
        progress_callback=None,
    ) -> TranscriptionResult:
        """轉錄多個音檔片段。

        Args:
            segments: 音檔片段列表。
            sample_rate: 取樣率。
            prompt: 字典提示文字。
            language: 語言代碼。
            progress_callback: 進度回呼 fn(current, total)。

        Returns:
            TranscriptionResult。
        """
        if not self.is_loaded:
            raise RuntimeError("模型尚未載入，請先呼叫 load_model()")

        result_segments: list[TranscriptionSegment] = []
        total = len(segments)

        # 建立 forced_decoder_ids（語言 + task）
        forced_decoder_ids = self._processor.get_decoder_prompt_ids(
            language=language, task="transcribe"
        )

        # 若有 prompt，先將其編碼為 prompt token ids
        prompt_ids = None
        if prompt:
            prompt_ids = self._processor.get_prompt_ids(prompt, return_tensors="np")
            prompt_ids = prompt_ids.tolist() if hasattr(prompt_ids, "tolist") else list(prompt_ids)

        for i, seg in enumerate(segments):
            logger.debug("轉錄片段 %d/%d (%.1fs - %.1fs)", i + 1, total, seg.start, seg.end)

            # 準備輸入特徵
            input_features = self._processor(
                seg.waveform, sampling_rate=sample_rate, return_tensors="pt"
            ).input_features
            input_features = input_features.to(
                device=self._device_info.device, dtype=self._device_info.dtype
            )

            # 生成（不使用 pipeline）
            # Whisper max_target_positions = 448，需扣除 decoder 起始 token 數量
            # forced_decoder_ids 佔的位置 + 1 個 SOT token
            prefix_len = len(forced_decoder_ids) + 1 if forced_decoder_ids else 1
            if prompt_ids is not None:
                prefix_len += len(prompt_ids)
            max_new = min(448, 448 - prefix_len)

            generate_kwargs = {
                "input_features": input_features,
                "forced_decoder_ids": forced_decoder_ids,
                "max_new_tokens": max_new,
            }
            if prompt_ids is not None:
                generate_kwargs["prompt_ids"] = torch.tensor(
                    prompt_ids, dtype=torch.long, device=self._device_info.device
                )

            with torch.no_grad():
                predicted_ids = self._model.generate(**generate_kwargs)

            # 解碼
            text = self._processor.batch_decode(
                predicted_ids, skip_special_tokens=True
            )[0].strip()

            result_segments.append(
                TranscriptionSegment(start=seg.start, end=seg.end, text=text)
            )

            if progress_callback:
                progress_callback(i + 1, total)

        full_text = "".join(seg.text for seg in result_segments)
        return TranscriptionResult(full_text=full_text, segments=result_segments)
