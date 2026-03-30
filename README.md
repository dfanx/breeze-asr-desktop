# Breeze ASR Desktop

基於 [MediaTek-Research/Breeze-ASR-25](https://huggingface.co/MediaTek-Research/Breeze-ASR-25) 模型的 Windows 桌面語音轉文字工具。

支援批次處理 MP3/WAV 音檔，自動分段辨識並匯出 TXT / SRT 字幕檔。

## 功能

- **GPU 加速辨識** — 自動偵測 NVIDIA GPU，支援 CUDA 加速
- **批次處理** — 拖放多個音檔或整個資料夾，一鍵開始轉錄
- **多種匯出格式** — TXT（逐段）、完整 TXT、SRT 字幕
- **字典功能** — 自訂常用詞彙，提升辨識準確度
- **模型管理** — 支援下載、切換、刪除模型
- **設定介面** — 輸出目錄、分段秒數、GPU 偏好等可自訂
- **背景轉錄** — 轉錄過程不凍結界面，可隨時停止

## 系統需求

| 項目 | 需求 |
|------|------|
| 作業系統 | Windows 10/11（64-bit） |
| GPU | NVIDIA GPU + CUDA 12.x（建議，無 GPU 會自動使用 CPU） |
| 記憶體 | 8 GB 以上 |
| 磁碟空間 | ~5 GB（含模型與執行環境） |

## 快速使用（免安裝）

1. 前往 [Releases](../../releases) 頁面下載最新版 `BreezeASRDesktop.zip`
2. 解壓縮到任意目錄
3. 執行 `BreezeASRDesktop.exe`
4. 首次啟動時，至「模型管理」下載 Breeze ASR 25 模型
5. 拖放或匯入音檔 → 點擊「開始」

> 若模型已在 HuggingFace 快取中（`~/.cache/huggingface/`），程式會自動偵測使用。

## 從原始碼執行

### 環境準備

```powershell
# Python 3.10+ 必須
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 安裝 PyTorch（CUDA 版本，依你的 CUDA 版本調整）
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu126

# 安裝其他依賴
pip install -r requirements.txt
```

### 啟動

```powershell
.\.venv\Scripts\Activate.ps1
python -m app.main
```

### 打包

```powershell
pip install pyinstaller
.\build.ps1
# 輸出: dist\BreezeASRDesktop\
```

## 專案結構

```
app/
├── main.py                 # 程式進入點
├── core/                   # 核心邏輯
│   ├── transcriber.py      # Whisper ASR 引擎
│   ├── audio_loader.py     # 音訊載入（librosa）
│   ├── audio_segmenter.py  # 音訊分段
│   ├── task_manager.py     # 任務佇列管理
│   ├── exporter.py         # TXT/SRT 匯出
│   ├── dictionary_manager.py  # 字典管理
│   ├── model_manager.py    # 模型註冊與切換
│   ├── downloader.py       # HuggingFace 模型下載
│   ├── device_manager.py   # GPU/CPU 偵測
│   └── logger.py           # 日誌系統
├── gui/                    # PySide6 GUI
│   ├── main_window.py      # 主視窗
│   ├── settings_dialog.py  # 設定對話框
│   ├── dictionary_dialog.py    # 字典編輯器
│   ├── model_manager_dialog.py # 模型管理
│   └── widgets/            # 自訂元件
├── config/                 # 預設設定檔
│   ├── default_config.json
│   └── model_registry.json
└── utils/                  # 工具模組
runtime/                    # 執行期目錄（自動建立）
├── config.json             # 使用者設定
├── Dictionary.txt          # 字典檔
├── output/                 # 辨識結果
├── logs/                   # 日誌
└── models/                 # 下載的模型
```

## 授權

本工具基於 [Breeze ASR 25](https://huggingface.co/MediaTek-Research/Breeze-ASR-25) 模型，模型授權請參閱其 HuggingFace 頁面。
