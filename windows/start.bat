@echo off
setlocal

cd /d "%~dp0"

echo ========================================================
echo   OmniDownloader - Windows Desktop Quick Launcher
echo ========================================================
echo.

:: 1. Check Python installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

:: 2. Setup or Locate Virtual Environment (local or parent)
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else if exist "..\venv\Scripts\activate.bat" (
    call ..\venv\Scripts\activate.bat
) else (
    echo [*] Creating Python virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    call venv\Scripts\activate.bat
)

:: 3. Install Dependencies
echo [*] Checking dependencies...
pip install -r backend\requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [WARNING] Retrying dependency check...
    pip install -r backend\requirements.txt
)

:: 4. Launch Standalone PC Desktop Window once server is verified listening
start "" powershell -NoProfile -Command "$client = New-Object System.Net.Sockets.TcpClient; for ($i=0; $i -lt 40; $i++) { try { $client.Connect('127.0.0.1', 8000); $client.Close(); $e86 = \"${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe\"; $e64 = \"${env:ProgramFiles}\Microsoft\Edge\Application\msedge.exe\"; $prof = \"$env:LOCALAPPDATA\OmniDownloader\AppShellProfile\"; $args = @('--app=http://localhost:8000', '--window-size=1120,820', '--app-id=OmniDownloader', \"--user-data-dir=$prof\", '--no-first-run', '--no-default-browser-check', '--disable-sync', '--disable-features=Sync,Signin,EdgeIdentitySignIn'); if (Test-Path $e86) { Start-Process $e86 -ArgumentList $args } elseif (Test-Path $e64) { Start-Process $e64 -ArgumentList $args } else { Start-Process 'http://localhost:8000' }; break } catch { Start-Sleep -Milliseconds 500 } }"

:: 5. Start FastAPI Application
echo.
echo ========================================================
echo   Server running at: http://localhost:8000
echo   Downloads saved to: %~dp0downloads
echo   Press CTRL+C in this window to stop the server.
echo ========================================================
echo.

cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

pause
