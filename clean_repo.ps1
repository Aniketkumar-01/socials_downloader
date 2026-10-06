# OmniDownloader - PowerShell Repository Cleanup Utility
param (
    [switch]$Silent = $false
)

$ErrorActionPreference = "SilentlyContinue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

if (-not $Silent) {
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  OmniDownloader - Repository Cleanup Utility" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Cleaning unnecessary files, temporary caches, and scratch data..." -ForegroundColor Yellow
}

# 1. Remove sensitive session credentials (keep cookies.txt.example only)
if (Test-Path "$ScriptDir\cookies.txt") {
    Remove-Item -Force "$ScriptDir\cookies.txt"
    git rm -f --cached "cookies.txt" 2>$null
}

# 2. Remove internal development specifications and scratch notes
$ScratchFiles = @(
    "SPEC-app-updater.md",
    "SPEC.md",
    "ARCHITECTURE.md",
    "DESIGN.md",
    "PRODUCT.md",
    "iterations_done.md",
    "desktop.py",
    "backend\tests\run_1000_iterations.py",
    "push.bat",
    "push.ps1",
    "push_to_github.bat"
)

foreach ($f in $ScratchFiles) {
    $fullPath = Join-Path $ScriptDir $f
    if (Test-Path $fullPath) {
        Remove-Item -Force $fullPath
        git rm -f --cached $f 2>$null
    }
}

# 3. Remove internal task directories
if (Test-Path "$ScriptDir\tasks") {
    Remove-Item -Recurse -Force "$ScriptDir\tasks"
    git rm -rf --cached "tasks" 2>$null
}

# 4. Remove agent and tooling scratch directories
if (Test-Path "$ScriptDir\.impeccable") { Remove-Item -Recurse -Force "$ScriptDir\.impeccable" }
if (Test-Path "$ScriptDir\.opencode") { Remove-Item -Recurse -Force "$ScriptDir\.opencode" }

# 5. Remove Python and test caches
if (Test-Path "$ScriptDir\.pytest_cache") { Remove-Item -Recurse -Force "$ScriptDir\.pytest_cache" }
if (Test-Path "$ScriptDir\backend\.pytest_cache") { Remove-Item -Recurse -Force "$ScriptDir\backend\.pytest_cache" }
Get-ChildItem -Path $ScriptDir -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Path $ScriptDir -Recurse -File -Include "*.pyc", "*.pyo", "*.pyd" | Remove-Item -Force

# 6. Remove OS metadata artifacts
Get-ChildItem -Path $ScriptDir -Recurse -File -Include ".DS_Store", "Thumbs.db", "desktop.ini" | Remove-Item -Force

if (-not $Silent) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "  Repository successfully cleaned!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
}
