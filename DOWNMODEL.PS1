# 1. 強制設定編碼，確保在舊版 Windows 下中文輸出不亂碼
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "[1/3] 正在檢查並更新 Python 環境套件..." -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan

# 2. 決定 Python 指令 (舊電腦可能只有 python 或只有 py)
$pyApp = "python"
$checkPy = python --version 2>$null
if ($? -eq $false) {
    $pyApp = "py"
}

# 更新 Pip 與必要套件
# 使用 & 呼叫變數指令，確保相容性
& $pyApp -m pip install --upgrade pip
& $pyApp -m pip install --upgrade torch torchaudio transformers datasets[audio] accelerate huggingface_hub

# 檢查上一個指令是否成功 (Win7/10 通用檢查)
if ($? -eq $false) {
    Write-Host "[錯誤] 套件安裝失敗，請檢查網路連線或 Python 是否已加入環境變數。" -ForegroundColor Red
    # 這裡不直接 exit，給使用者看清楚錯誤的機會
    pause
    exit
}

Write-Host "`n[2/3] 正在檢查模型檔案 (MediaTek-Research/Breeze-ASR-25)..." -ForegroundColor Cyan

# 3. 內嵌 Python 邏輯：使用 @" "@ 符號確保語法不被 PowerShell 誤判
$pythonCode = @"
import os
import sys
try:
    from huggingface_hub import scan_cache_dir
    from transformers import WhisperProcessor, WhisperForConditionalGeneration
except ImportError:
    print('[錯誤] 必要的 Python 套件尚未安裝成功。')
    sys.exit(1)

model_id = 'MediaTek-Research/Breeze-ASR-25'

def cleanup_corrupted_models():
    print(f'[資訊] 正在掃描快取以清理毀損檔案...')
    try:
        # 嘗試使用 cli 進行精準清理
        os.system(f'huggingface-cli delete-cache --repo-id {model_id} --force')
    except Exception as e:
        print(f'[錯誤] 清理過程發生問題: {e}')

try:
    print(f'[執行] 嘗試載入模型 {model_id}...')
    processor = WhisperProcessor.from_pretrained(model_id)
    model = WhisperForConditionalGeneration.from_pretrained(model_id)
    print(f'[成功] 模型已正確下載並載入。')
except Exception as e:
    print(f'[警告] 下載失敗或檔案毀損，準備重試...')
    cleanup_corrupted_models()
    try:
        processor = WhisperProcessor.from_pretrained(model_id)
        model = WhisperForConditionalGeneration.from_pretrained(model_id)
        print(f'[成功] 第二次重試載入完成。')
    except Exception as e2:
        print(f'[嚴重錯誤] 重試後依然失敗: {e2}')
        sys.exit(1)
"@

# 呼叫 Python 執行邏輯 (確保使用前面偵測到的 $pyApp)
# 使用 Write-Output 傳遞字串避免管道編碼出錯
Write-Output $pythonCode | & $pyApp -

if ($? -eq $false) {
    Write-Host "[失敗] 模型下載過程中發生無法排除的錯誤。" -ForegroundColor Red
    pause
    exit
}

Write-Host "`n[3/3] 所有的執行環境與模型已準備就緒！" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green