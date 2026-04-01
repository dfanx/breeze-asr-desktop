<#
.SYNOPSIS
    Breeze ASR Desktop — 一鍵環境建構腳本
.DESCRIPTION
    在全新 Windows 電腦上自動安裝 Python、建立虛擬環境、安裝所有依賴套件。
    完成後可直接執行 build.ps1 打包，或 python app/main.py 啟動程式。
.NOTES
    執行前請確認:
    1. 以「系統管理員」身分開啟 PowerShell（安裝 Python 需要）
    2. 需要網路連線
    3. 如果 PowerShell 執行原則受限，先執行:
       Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.USAGE
    以系統管理員開啟 PowerShell，cd 到專案目錄，執行:
    .\setup_env.ps1
#>

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ROOT

# ═══════════════════════════════════════════════════════════════
#  設定區 — 可依需求調整
# ═══════════════════════════════════════════════════════════════
$PYTHON_VERSION      = "3.13.5"
$PYTHON_MAJOR_MINOR  = "313"
$VENV_DIR            = ".venv"
$TORCH_INDEX_URL     = "https://download.pytorch.org/whl/cu126"

# ═══════════════════════════════════════════════════════════════
#  工具函式
# ═══════════════════════════════════════════════════════════════
function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "──────────────────────────────────────────" -ForegroundColor Cyan
    Write-Host "  $Message" -ForegroundColor Cyan
    Write-Host "──────────────────────────────────────────" -ForegroundColor Cyan
}

function Write-OK {
    param([string]$Message)
    Write-Host "  ✓ $Message" -ForegroundColor Green
}

function Write-Skip {
    param([string]$Message)
    Write-Host "  → 略過: $Message" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Message)
    Write-Host "  ✗ $Message" -ForegroundColor Red
}

function Test-CommandExists {
    param([string]$Command)
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

# ═══════════════════════════════════════════════════════════════
#  步驟 1: 檢查 / 安裝 Python
# ═══════════════════════════════════════════════════════════════
Write-Step "步驟 1/5: 檢查 Python $PYTHON_VERSION"

$pythonCmd = $null

# 優先檢查系統上是否已有合適的 Python
foreach ($candidate in @("python", "python3", "py")) {
    if (Test-CommandExists $candidate) {
        $ver = & $candidate --version 2>&1
        if ($ver -match "Python 3\.13") {
            $pythonCmd = $candidate
            Write-OK "找到已安裝的 Python: $ver"
            break
        }
    }
}

# 如果已有 py launcher，嘗試指定版本
if (-not $pythonCmd -and (Test-CommandExists "py")) {
    try {
        $ver = & py -3.13 --version 2>&1
        if ($ver -match "Python 3\.13") {
            $pythonCmd = "py -3.13"
            Write-OK "找到已安裝的 Python (via py launcher): $ver"
        }
    } catch {}
}

if (-not $pythonCmd) {
    Write-Host "  未找到 Python 3.13，開始下載安裝..." -ForegroundColor Yellow

    $installerName = "python-$PYTHON_VERSION-amd64.exe"
    $installerUrl  = "https://www.python.org/ftp/python/$PYTHON_VERSION/$installerName"
    $installerPath = Join-Path $env:TEMP $installerName

    # 下載
    if (-not (Test-Path $installerPath)) {
        Write-Host "  下載中: $installerUrl" -ForegroundColor Gray
        try {
            Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing
        } catch {
            Write-Fail "下載 Python 安裝檔失敗: $_"
            Write-Host "  請手動下載 Python 3.13.x 並安裝後重新執行此腳本" -ForegroundColor Yellow
            Write-Host "  下載頁面: https://www.python.org/downloads/" -ForegroundColor Yellow
            exit 1
        }
        Write-OK "下載完成: $installerPath"
    } else {
        Write-Skip "安裝檔已存在: $installerPath"
    }

    # 靜默安裝（加入 PATH、安裝 pip、安裝 py launcher）
    Write-Host "  正在安裝 Python（需要系統管理員權限）..." -ForegroundColor Gray
    $installArgs = @(
        "/quiet"
        "InstallAllUsers=1"
        "PrependPath=1"
        "Include_pip=1"
        "Include_launcher=1"
        "Include_test=0"
    )

    $proc = Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait -PassThru
    if ($proc.ExitCode -ne 0) {
        Write-Fail "Python 安裝失敗 (exit code: $($proc.ExitCode))"
        Write-Host "  可能原因: 未以系統管理員身分執行" -ForegroundColor Yellow
        Write-Host "  請右鍵 PowerShell → 以系統管理員身分執行，再重新執行此腳本" -ForegroundColor Yellow
        exit 1
    }

    # 刷新 PATH（避免需要重開終端）
    $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath    = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path    = "$machinePath;$userPath"

    # 驗證安裝
    if (Test-CommandExists "python") {
        $pythonCmd = "python"
    } elseif (Test-CommandExists "py") {
        $pythonCmd = "py -3.13"
    } else {
        # 嘗試常見安裝路徑
        $defaultPythonPath = "C:\Program Files\Python$PYTHON_MAJOR_MINOR\python.exe"
        if (Test-Path $defaultPythonPath) {
            $pythonCmd = "`"$defaultPythonPath`""
        } else {
            Write-Fail "Python 安裝後仍無法找到，請手動確認安裝是否成功"
            exit 1
        }
    }

    $ver = Invoke-Expression "$pythonCmd --version" 2>&1
    Write-OK "Python 安裝完成: $ver"
}

# ═══════════════════════════════════════════════════════════════
#  步驟 2: 建立虛擬環境
# ═══════════════════════════════════════════════════════════════
Write-Step "步驟 2/5: 建立虛擬環境"

if (Test-Path "$VENV_DIR\Scripts\python.exe") {
    Write-Skip "虛擬環境已存在: $VENV_DIR"
} else {
    Write-Host "  建立虛擬環境: $VENV_DIR ..." -ForegroundColor Gray
    Invoke-Expression "$pythonCmd -m venv $VENV_DIR"
    if (-not (Test-Path "$VENV_DIR\Scripts\python.exe")) {
        Write-Fail "虛擬環境建立失敗"
        exit 1
    }
    Write-OK "虛擬環境已建立"
}

# 啟用虛擬環境
& "$VENV_DIR\Scripts\Activate.ps1"
Write-OK "虛擬環境已啟用"

# 升級 pip
Write-Host "  升級 pip..." -ForegroundColor Gray
python -m pip install --upgrade pip --quiet
Write-OK "pip 已升級"

# ═══════════════════════════════════════════════════════════════
#  步驟 3: 安裝 PyTorch (CUDA 12.6)
# ═══════════════════════════════════════════════════════════════
Write-Step "步驟 3/5: 安裝 PyTorch + CUDA 12.6"

# PyTorch 必須從專用 index 安裝，且必須在其他套件之前
# 以確保 numpy 等相容版本正確解析
Write-Host "  安裝 torch, torchaudio, torchvision（這可能需要幾分鐘）..." -ForegroundColor Gray

pip install `
    torch==2.11.0+cu126 `
    torchaudio==2.11.0+cu126 `
    torchvision==0.26.0+cu126 `
    --index-url $TORCH_INDEX_URL `
    --quiet

if ($LASTEXITCODE -ne 0) {
    Write-Fail "PyTorch 安裝失敗"
    Write-Host "  若無 NVIDIA GPU，可改用 CPU 版:" -ForegroundColor Yellow
    Write-Host "  pip install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/cpu" -ForegroundColor Yellow
    exit 1
}
Write-OK "PyTorch + CUDA 12.6 安裝完成"

# ═══════════════════════════════════════════════════════════════
#  步驟 4: 安裝其餘 Python 套件
# ═══════════════════════════════════════════════════════════════
Write-Step "步驟 4/5: 安裝其餘 Python 套件"

# 核心 AI / 音訊套件（有特定版本需求）
$corePkgs = @(
    "transformers==5.4.0"
    "accelerate==1.13.0"
    "huggingface_hub==1.8.0"
    "safetensors==0.7.0"
    "tokenizers==0.22.2"
    "sentencepiece==0.2.1"
)

# 音訊處理
$audioPkgs = @(
    "librosa==0.11.0"
    "soundfile==0.13.1"
    "soxr==1.0.0"
    "audioread==3.1.0"
    "audioop-lts==0.2.2"
)

# GUI
$guiPkgs = @(
    "PySide6==6.11.0"
)

# 科學計算
$sciPkgs = @(
    "numpy==2.4.3"
    "scipy==1.17.1"
    "scikit-learn==1.8.0"
    "numba==0.64.0"
    "llvmlite==0.46.0"
)

# 工具 / 網路 / 其他
$utilPkgs = @(
    "imageio-ffmpeg==0.6.0"
    "requests==2.33.0"
    "httpx==0.28.1"
    "tqdm==4.67.3"
    "PyYAML==6.0.3"
    "regex==2026.3.32"
    "pillow==12.1.1"
    "psutil==7.2.2"
    "rich==14.3.3"
    "colorama==0.4.6"
    "packaging==26.0"
    "filelock==3.25.2"
    "platformdirs==4.9.4"
    "Jinja2==3.1.6"
    "sympy==1.14.0"
    "pooch==1.9.0"
    "hf-xet==1.4.2"
    "msgpack==1.1.2"
    "cffi==2.0.0"
    "typing_extensions==4.15.0"
)

# 打包工具
$buildPkgs = @(
    "pyinstaller==6.19.0"
)

$allGroups = @(
    @{ Name = "核心 AI 套件";   Packages = $corePkgs }
    @{ Name = "音訊處理套件";   Packages = $audioPkgs }
    @{ Name = "GUI 套件";       Packages = $guiPkgs }
    @{ Name = "科學計算套件";   Packages = $sciPkgs }
    @{ Name = "工具/網路套件";  Packages = $utilPkgs }
    @{ Name = "打包工具";       Packages = $buildPkgs }
)

foreach ($group in $allGroups) {
    Write-Host "  安裝 $($group.Name)..." -ForegroundColor Gray
    $pkgList = $group.Packages -join " "
    Invoke-Expression "pip install $pkgList --quiet"
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "$($group.Name) 安裝失敗，嘗試逐一安裝..."
        foreach ($pkg in $group.Packages) {
            pip install $pkg --quiet
            if ($LASTEXITCODE -ne 0) {
                Write-Fail "  無法安裝: $pkg"
            } else {
                Write-OK "  $pkg"
            }
        }
    } else {
        Write-OK "$($group.Name) ($($group.Packages.Count) 個套件)"
    }
}

# ═══════════════════════════════════════════════════════════════
#  步驟 5: 建立 runtime 目錄 & 驗證
# ═══════════════════════════════════════════════════════════════
Write-Step "步驟 5/5: 建立 runtime 目錄 & 驗證安裝"

# 建立必要目錄
$runtimeDirs = @("runtime\output", "runtime\logs", "runtime\models", "runtime\temp")
foreach ($d in $runtimeDirs) {
    if (-not (Test-Path $d)) {
        New-Item -ItemType Directory -Path $d -Force | Out-Null
    }
}
Write-OK "runtime 目錄已建立"

# 驗證關鍵套件可正常匯入
Write-Host "  驗證關鍵套件..." -ForegroundColor Gray
$verifyScript = @"
import sys
errors = []
checks = [
    ('torch', 'import torch; print(f"  torch {torch.__version__}, CUDA={torch.cuda.is_available()}")'),
    ('torchaudio', 'import torchaudio'),
    ('transformers', 'import transformers'),
    ('huggingface_hub', 'import huggingface_hub'),
    ('librosa', 'import librosa'),
    ('soundfile', 'import soundfile'),
    ('PySide6', 'from PySide6.QtWidgets import QApplication'),
    ('numpy', 'import numpy'),
    ('scipy', 'import scipy'),
    ('accelerate', 'import accelerate'),
    ('imageio_ffmpeg', 'import imageio_ffmpeg'),
    ('pyinstaller', 'import PyInstaller'),
]
for name, code in checks:
    try:
        exec(code)
        print(f'  OK: {name}')
    except Exception as e:
        errors.append(f'{name}: {e}')
        print(f'  FAIL: {name} - {e}')
if errors:
    sys.exit(1)
"@

python -c $verifyScript
$verifyOK = ($LASTEXITCODE -eq 0)

# ═══════════════════════════════════════════════════════════════
#  完成
# ═══════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
if ($verifyOK) {
    Write-Host "  環境建構完成！所有套件驗證通過"                   -ForegroundColor Green
} else {
    Write-Host "  環境建構完成（部分套件驗證失敗，請查看上方訊息）" -ForegroundColor Yellow
}
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "  後續操作:" -ForegroundColor White
Write-Host "    啟用環境:  .\.venv\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "    直接執行:  python app\main.py" -ForegroundColor Gray
Write-Host "    打包 exe:  .\build.ps1" -ForegroundColor Gray
Write-Host "    下載模型:  python app\main.py --download-model" -ForegroundColor Gray
Write-Host ""
