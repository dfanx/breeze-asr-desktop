<#
.SYNOPSIS
    Breeze ASR Desktop — 一鍵環境建構腳本 (Windows 7/10/11 全相容版)
#>

# 1. 環境初始化：強制設定編碼與網路協定
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 強制啟用 TLS 1.2，否則 Windows 7 無法下載 Python 安裝檔
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# 取得腳本所在目錄，確保路徑含空格時也能運作
$ROOT = Get-Location
if ($PSScriptRoot) { $ROOT = $PSScriptRoot }
Set-Location "$ROOT"

# ═══════════════════════════════════════════════════════════════
#  設定區
# ═══════════════════════════════════════════════════════════════
$PYTHON_VERSION      = "3.13.5"
$VENV_DIR            = ".venv"
$TORCH_INDEX_URL     = "https://download.pytorch.org/whl/cu126"

# 顯示功能
function Write-Step {
    param([string]$Message)
    Write-Host "`n──────────────────────────────────────────" -ForegroundColor Cyan
    Write-Host "  $Message" -ForegroundColor Cyan
    Write-Host "──────────────────────────────────────────" -ForegroundColor Cyan
}

# ═══════════════════════════════════════════════════════════════
#  步驟 1: 檢查 / 安裝 Python 3.13
# ═══════════════════════════════════════════════════════════════
Write-Step "步驟 1/3: 檢查 Python 環境"

$pythonCmd = $null
# 檢查現有版本
foreach ($candidate in @("python", "python3", "py")) {
    $check = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($check) {
        $ver = & $candidate --version 2>&1
        if ("$ver" -match "3\.13") {
            $pythonCmd = $candidate
            Write-Host "  ✓ 找到 Python: $ver" -ForegroundColor Green
            break
        }
    }
}

# 若無 Python 則下載安裝
if ($null -eq $pythonCmd) {
    Write-Host "  未找到 Python 3.13，準備下載安裝..." -ForegroundColor Yellow
    $installerName = "python-$PYTHON_VERSION-amd64.exe"
    $installerUrl  = "https://www.python.org/ftp/python/$PYTHON_VERSION/$installerName"
    $installerPath = Join-Path $env:TEMP $installerName

    if (-not (Test-Path "$installerPath")) {
        Write-Host "  正在下載 Python 安裝檔..." -ForegroundColor Gray
        Invoke-WebRequest -Uri $installerUrl -OutFile "$installerPath" -UseBasicParsing
    }

    Write-Host "  正在執行靜默安裝（請稍候）..." -ForegroundColor Gray
    $installArgs = "/quiet InstallAllUsers=1 PrependPath=1 Include_pip=1"
    $proc = Start-Process -FilePath "$installerPath" -ArgumentList $installArgs -Wait -PassThru
    
    # 刷新環境變數
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    $pythonCmd = "python"
}

# ═══════════════════════════════════════════════════════════════
#  步驟 2: 建立與啟用虛擬環境
# ═══════════════════════════════════════════════════════════════
Write-Step "步驟 2/3: 建立虛擬環境 (.venv)"

if (-not (Test-Path "$ROOT\$VENV_DIR\Scripts\python.exe")) {
    Write-Host "  正在建立虛擬環境..." -ForegroundColor Gray
    & $pythonCmd -m venv "$VENV_DIR"
}

# 啟用虛擬環境 (使用傳統寫法確保相容性)
$activateScript = "$ROOT\$VENV_DIR\Scripts\Activate.ps1"
if (Test-Path "$activateScript") {
    . "$activateScript"
    Write-Host "  ✓ 虛擬環境已啟用" -ForegroundColor Green
} else {
    Write-Host "  ✗ 錯誤：無法啟動虛擬環境" -ForegroundColor Red
    pause
    exit
}

# ═══════════════════════════════════════════════════════════════
#  步驟 3: 安裝套件與模型檢查
# ═══════════════════════════════════════════════════════════════
Write-Step "步驟 3/3: 安裝 AI 套件與驗證模型"

Write-Host "  1. 升級 Pip..." -ForegroundColor Gray
python -m pip install --upgrade pip --quiet

Write-Host "  2. 安裝 PyTorch + Transformers (Breeze-ASR 需求)..." -ForegroundColor Gray
# 建議將所有套件合併安裝以減少衝突
pip install torch torchaudio transformers accelerate datasets[audio] huggingface_hub --index-url $TORCH_INDEX_URL --quiet

# 模型下載與清理邏輯 (封裝在 Python 內部執行，避免 PowerShell 語法錯誤)
Write-Host "  3. 驗證模型檔案 (MediaTek-Research/Breeze-ASR-25)..." -ForegroundColor Gray
$pyCode = @"
import os
import sys
from transformers import WhisperProcessor, WhisperForConditionalGeneration
model_id = 'MediaTek-Research/Breeze-ASR-25'
try:
    print(f'  [執行] 載入模型中...')
    WhisperProcessor.from_pretrained(model_id)
    WhisperForConditionalGeneration.from_pretrained(model_id)
    print(f'  [成功] 模型已就緒。')
except Exception as e:
    print(f'  [警告] 偵測到毀損，嘗試清理重新下載: {e}')
    os.system(f'huggingface-cli delete-cache --repo-id {model_id} --force')
    WhisperProcessor.from_pretrained(model_id)
    WhisperForConditionalGeneration.from_pretrained(model_id)
    print(f'  [成功] 模型重新下載完成。')
"@

# 執行驗證程式碼
$pyCode | python

# ═══════════════════════════════════════════════════════════════
#  結尾
# ═══════════════════════════════════════════════════════════════
Write-Host "`n===============================================" -ForegroundColor Green
Write-Host "  恭喜！環境建構完成。" -ForegroundColor Green
Write-Host "  現在你可以執行: python app/main.py" -ForegroundColor White
Write-Host "===============================================" -ForegroundColor Green

pause