@echo off
echo ============================================================
echo   OmniDownloader - Build Standalone EXE ^& Windows Installer
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/4] Checking Python environment...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b 1
)

echo [2/4] Generating application icon and assets...
python -m pip install pillow >nul 2>nul
python create_icon.py

echo.
echo [3/4] Compiling OmniDownloader.exe with PyInstaller...
python -m pip install -r backend/requirements.txt pyinstaller
pyinstaller --clean omnidownloader.spec

if %errorlevel% neq 0 (
    echo.
    echo ============================================================
    echo   Error: PyInstaller build failed. Check output above.
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo [4/4] Checking for Inno Setup compiler (ISCC)...
set "ISCC_EXE="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

if not defined ISCC_EXE (
    where iscc >nul 2>nul
    if %errorlevel% equ 0 set "ISCC_EXE=iscc"
)

if defined ISCC_EXE (
    echo Compiling Windows Installer (OmniDownloader-Setup.exe)...
    "%ISCC_EXE%" installer.iss
    if %errorlevel% equ 0 (
        echo.
        echo ============================================================
        echo   BUILD SUCCESSFUL!
        echo.
        echo   [1] Windows Installer:  dist\OmniDownloader-Setup.exe
        echo   [2] Portable Binary:    dist\OmniDownloader.exe
        echo ============================================================
    ) else (
        echo.
        echo [WARN] Inno Setup compilation encountered an issue.
        echo Portable binary is still ready at: dist\OmniDownloader.exe
    )
) else (
    echo.
    echo [INFO] Inno Setup is not installed locally.
    echo Portable executable is ready at: dist\OmniDownloader.exe
    echo.
    echo To build the setup installer locally, install Inno Setup:
    echo   winget install JRSoftware.InnoSetup
    echo (GitHub Actions CI compiles the installer automatically!)
)

echo.
pause
