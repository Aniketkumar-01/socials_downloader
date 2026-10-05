@echo off
echo ============================================================
echo   OmniDownloader - Build Standalone Windows .exe
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/3] Checking Python installation...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b 1
)

echo [2/3] Installing dependencies and PyInstaller...
pip install -r backend/requirements.txt pyinstaller

echo.
echo [3/3] Building OmniDownloader.exe with PyInstaller...
pyinstaller --clean omnidownloader.spec

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo   BUILD SUCCESSFUL!
    echo   Executable is ready at: dist\OmniDownloader.exe
    echo   Double-click dist\OmniDownloader.exe to run the application!
    echo ============================================================
) else (
    echo.
    echo ============================================================
    echo   Error: Build failed. Check the error output above.
    echo ============================================================
)

echo.
pause
