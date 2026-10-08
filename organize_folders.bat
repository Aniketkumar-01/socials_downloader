@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   OmniDownloader - Folder Organization Utility
echo   Moving Windows Desktop files into windows\
echo ========================================================
echo.

cd /d "%~dp0"

if not exist "windows" (
    mkdir windows
)

where git >nul 2>nul
if %errorlevel% equ 0 (
    echo [*] Git detected. Moving files with git tracking...
    if exist "backend" git mv backend windows/ 2>nul || move backend windows\
    if exist "frontend" git mv frontend windows/ 2>nul || move frontend windows\
    if exist "launcher.py" git mv launcher.py windows/ 2>nul || move launcher.py windows\
    if exist "installer.iss" git mv installer.iss windows/ 2>nul || move installer.iss windows\
    if exist "omnidownloader.spec" git mv omnidownloader.spec windows/ 2>nul || move omnidownloader.spec windows\
    if exist "create_icon.py" git mv create_icon.py windows/ 2>nul || move create_icon.py windows\
    if exist "cookies.txt.example" git mv cookies.txt.example windows/ 2>nul || move cookies.txt.example windows\
) else (
    echo [*] Moving files to windows\...
    if exist "backend" move backend windows\
    if exist "frontend" move frontend windows\
    if exist "launcher.py" move launcher.py windows\
    if exist "installer.iss" move installer.iss windows\
    if exist "omnidownloader.spec" move omnidownloader.spec windows\
    if exist "create_icon.py" move create_icon.py windows\
    if exist "cookies.txt.example" move cookies.txt.example windows\
)

echo.
echo [SUCCESS] Windows application files organized into windows\ folder!
echo           Android application files are located in android\ folder.
echo.
pause
