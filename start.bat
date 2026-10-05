@echo off
setlocal

echo ========================================================
echo   YouTube Video and Playlist Downloader - Quick Launcher
echo ========================================================
echo.

cd /d "%~dp0"

:: Cleanup obsolete scratch and specification files
if exist "create_icon.py" del /f /q "create_icon.py" 2>nul
if exist "iterations_done.md" del /f /q "iterations_done.md" 2>nul
if exist "backend\tests\run_1000_iterations.py" del /f /q "backend\tests\run_1000_iterations.py" 2>nul
if exist ".pytest_cache" rd /s /q ".pytest_cache" 2>nul
if exist "tasks" rd /s /q "tasks" 2>nul
if exist "SPEC.md" del /f /q "SPEC.md" 2>nul
if exist "ARCHITECTURE.md" del /f /q "ARCHITECTURE.md" 2>nul

:: 1. Check Python installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

:: 2. Setup Virtual Environment
if not exist "venv" (
    echo [*] Creating Python virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: 3. Activate Virtual Environment
echo [*] Activating virtual environment...
call venv\Scripts\activate.bat

:: 4. Install Dependencies
echo [*] Checking dependencies...
pip install -r backend\requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [WARNING] Retrying dependency check...
    pip install -r backend\requirements.txt
)

:: 5. Launch Standalone PC Desktop Window once server is verified listening
start "" powershell -NoProfile -Command "for ($i=0; $i -lt 40; $i++) { try { $client = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 8000); $client.Close(); $e86 = \"${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe\"; $e64 = \"${env:ProgramFiles}\Microsoft\Edge\Application\msedge.exe\"; if (Test-Path $e86) { Start-Process $e86 -ArgumentList '--app=http://localhost:8000','--window-size=1120,820','--app-id=OmniDownloader' } elseif (Test-Path $e64) { Start-Process $e64 -ArgumentList '--app=http://localhost:8000','--window-size=1120,820','--app-id=OmniDownloader' } else { Start-Process 'http://localhost:8000' }; break } catch { Start-Sleep -Milliseconds 500 } }"

:: 6. Start FastAPI Application
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

