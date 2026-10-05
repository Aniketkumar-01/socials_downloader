# OmniDownloader - Developer Bootstrap & Startup Script
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  OmniDownloader - Developer Quick Start" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verify Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[1/3] Python environment: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python was not found in PATH. Please install Python 3.10+ from python.org." -ForegroundColor Red
    exit 1
}

# 2. Virtual Environment Setup
$VenvDir = Join-Path $RepoRoot "venv"
if (-not (Test-Path $VenvDir)) {
    Write-Host "[2/3] Initializing virtual environment in venv/..." -ForegroundColor Yellow
    python -m venv "$VenvDir"
}

$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
if (Test-Path $ActivateScript) {
    & $ActivateScript
}

# 3. Dependencies
Write-Host "[3/3] Checking and installing dependencies..." -ForegroundColor Yellow
python -m pip install -r "$RepoRoot\backend\requirements.txt" --quiet

Write-Host ""
Write-Host "Starting OmniDownloader desktop application..." -ForegroundColor Cyan
python "$RepoRoot\launcher.py"
