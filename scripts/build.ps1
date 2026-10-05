# OmniDownloader - Unified Local Build Script
param (
    [ValidateSet("All", "Exe", "Installer")]
    [string]$Target = "All"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  OmniDownloader - Build Script [Target: $Target]" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python
try {
    $pyVer = python --version 2>&1
    Write-Host "[1/4] Found Python: $pyVer" -ForegroundColor Green
} catch {
    Write-Error "Python is not installed or not in PATH."
    exit 1
}

# 2. Verify / Generate Application Icon & Offline Fonts
Write-Host "[2/4] Verifying application assets and offline fonts..." -ForegroundColor Yellow
$icoPath = Join-Path $RepoRoot "assets\app.ico"
if (-not (Test-Path $icoPath)) {
    Write-Host "  Icon not found. Generating assets via tools\create_icon.py..."
    python "$RepoRoot\tools\create_icon.py"
}
python "$RepoRoot\tools\download_fonts.py"

# 3. Build Portable Executable
if ($Target -eq "All" -or $Target -eq "Exe") {
    Write-Host ""
    Write-Host "[3/4] Compiling OmniDownloader.exe with PyInstaller..." -ForegroundColor Yellow
    pyinstaller --clean omnidownloader.spec
    
    $exePath = Join-Path $RepoRoot "dist\OmniDownloader.exe"
    if (-not (Test-Path $exePath)) {
        Write-Error "PyInstaller build failed: dist\OmniDownloader.exe was not created."
        exit 1
    }
    $exeSize = (Get-Item $exePath).Length / 1MB
    Write-Host "  [SUCCESS] Portable binary: $exePath ($([math]::Round($exeSize, 2)) MB)" -ForegroundColor Green
}

# 4. Build Windows Installer with Inno Setup
if ($Target -eq "All" -or $Target -eq "Installer") {
    Write-Host ""
    Write-Host "[4/4] Checking for Inno Setup compiler (ISCC)..." -ForegroundColor Yellow
    
    $isccCandidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    )
    $iscc = $null
    foreach ($cand in $isccCandidates) {
        if (Test-Path $cand) {
            $iscc = $cand
            break
        }
    }
    if (-not $iscc) {
        $cmd = Get-Command iscc.exe -ErrorAction SilentlyContinue
        if ($cmd) { $iscc = $cmd.Source }
    }

    if ($iscc) {
        Write-Host "  Compiling installer using: $iscc" -ForegroundColor Yellow
        & $iscc "$RepoRoot\installer.iss"
        $setupPath = Join-Path $RepoRoot "dist\OmniDownloader-Setup.exe"
        if (Test-Path $setupPath) {
            $setupSize = (Get-Item $setupPath).Length / 1MB
            Write-Host "  [SUCCESS] Windows Installer: $setupPath ($([math]::Round($setupSize, 2)) MB)" -ForegroundColor Green
        } else {
            Write-Warning "Inno Setup failed to create dist\OmniDownloader-Setup.exe."
        }
    } else {
        Write-Host "  [INFO] Inno Setup is not installed locally." -ForegroundColor DarkYellow
        Write-Host "  To compile the Windows Setup wizard locally: winget install JRSoftware.InnoSetup" -ForegroundColor DarkYellow
        Write-Host "  (GitHub Actions CI compiles both the EXE and Setup wizard automatically on release tags)." -ForegroundColor DarkYellow
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Build process completed for target: $Target" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
