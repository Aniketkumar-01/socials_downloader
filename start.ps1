# YouTube Downloader PowerShell Launcher
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Cleanup obsolete scratch and specification files
if (Test-Path "$ScriptDir\iterations_done.md") { Remove-Item -Force "$ScriptDir\iterations_done.md" -ErrorAction SilentlyContinue }
if (Test-Path "$ScriptDir\backend\tests\run_1000_iterations.py") { Remove-Item -Force "$ScriptDir\backend\tests\run_1000_iterations.py" -ErrorAction SilentlyContinue }
if (Test-Path "$ScriptDir\.pytest_cache") { Remove-Item -Recurse -Force "$ScriptDir\.pytest_cache" -ErrorAction SilentlyContinue }
if (Test-Path "$ScriptDir\tasks") { Remove-Item -Recurse -Force "$ScriptDir\tasks" -ErrorAction SilentlyContinue }
if (Test-Path "$ScriptDir\SPEC.md") { Remove-Item -Force "$ScriptDir\SPEC.md" -ErrorAction SilentlyContinue }
if (Test-Path "$ScriptDir\ARCHITECTURE.md") { Remove-Item -Force "$ScriptDir\ARCHITECTURE.md" -ErrorAction SilentlyContinue }
if (Test-Path "$ScriptDir\DESIGN.md") { Remove-Item -Force "$ScriptDir\DESIGN.md" -ErrorAction SilentlyContinue }
if (Test-Path "$ScriptDir\PRODUCT.md") { Remove-Item -Force "$ScriptDir\PRODUCT.md" -ErrorAction SilentlyContinue }
if (Test-Path "$ScriptDir\desktop.py") { Remove-Item -Force "$ScriptDir\desktop.py" -ErrorAction SilentlyContinue }
if (Test-Path "$ScriptDir\push.bat") { Remove-Item -Force "$ScriptDir\push.bat" -ErrorAction SilentlyContinue }

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  YouTube Video & Playlist Downloader - Quick Launcher" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[*] Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python was not found in PATH. Please install Python 3.10+ from python.org." -ForegroundColor Red
    Read-Host "Press Enter to exit..."
    exit 1
}

# 2. Check/create venv
$VenvDir = Join-Path $ScriptDir "venv"
if (-not (Test-Path $VenvDir)) {
    Write-Host "[*] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# 3. Activate venv
$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
if (Test-Path $ActivateScript) {
    & $ActivateScript
}

# 4. Install dependencies
Write-Host "[*] Checking and installing dependencies..." -ForegroundColor Yellow
pip install -r backend\requirements.txt --quiet

# 5. Launch Standalone PC Desktop Window once server is listening
Start-Job -ScriptBlock {
    for ($i = 0; $i -lt 40; $i++) {
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 8000)
            $tcp.Close()
            $edge86 = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
            $edge64 = "${env:ProgramFiles}\Microsoft\Edge\Application\msedge.exe"
            $edgeProfile = Join-Path $env:LOCALAPPDATA "OmniDownloader\AppShellProfile"
            $edgeArgs = @(
                "--app=http://localhost:8000",
                "--window-size=1120,820",
                "--app-id=OmniDownloader",
                "--user-data-dir=$edgeProfile",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-sync",
                "--disable-features=Sync,Signin,EdgeIdentitySignIn"
            )
            if (Test-Path $edge86) {
                Start-Process $edge86 -ArgumentList $edgeArgs
            } elseif (Test-Path $edge64) {
                Start-Process $edge64 -ArgumentList $edgeArgs
            } else {
                Start-Process "http://localhost:8000"
            }
            break
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
} | Out-Null

# 6. Run FastAPI
Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  Server running at: http://localhost:8000" -ForegroundColor Green
Write-Host "  Downloads folder:  $ScriptDir\downloads" -ForegroundColor Green
Write-Host "  Press CTRL+C to stop the server." -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""

Set-Location (Join-Path $ScriptDir "backend")
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
