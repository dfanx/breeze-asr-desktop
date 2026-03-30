$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ROOT

# 啟用虛擬環境
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    & ".\.venv\Scripts\Activate.ps1"
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Breeze ASR Desktop — Build"            -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 清除舊產物
if (Test-Path ".\dist\BreezeASRDesktop") {
    Write-Host "清除舊 dist..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force ".\dist\BreezeASRDesktop"
}

# 執行 PyInstaller
Write-Host "執行 PyInstaller..." -ForegroundColor Yellow
pyinstaller BreezeASRDesktop.spec --noconfirm --clean

if ($LASTEXITCODE -ne 0) {
    Write-Host "打包失敗！" -ForegroundColor Red
    exit 1
}

# 建立 runtime 目錄結構
$distRoot = ".\dist\BreezeASRDesktop"
$runtimeDirs = @("runtime\output", "runtime\logs", "runtime\models")
foreach ($d in $runtimeDirs) {
    $p = Join-Path $distRoot $d
    if (-not (Test-Path $p)) {
        New-Item -ItemType Directory -Path $p -Force | Out-Null
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  打包完成！" -ForegroundColor Green
Write-Host "  輸出: dist\BreezeASRDesktop\"          -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
