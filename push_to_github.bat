@echo off
echo ============================================================
echo   OmniDownloader - Git Setup & GitHub Push
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/5] Checking Git installation...
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Git is not installed or not in PATH. Please install Git for Windows.
    pause
    exit /b 1
)

echo [2/5] Initializing Git repository...
if not exist ".git" (
    git init -b main
)

echo [3/5] Staging files (.gitignore protects cookies.txt and venv)...
git add .

echo [4/5] Creating commit...
git commit -m "feat: complete UI redesign with sleek obsidian console and unified action hub"

echo [5/5] Setting remote and pushing to GitHub...
git remote remove origin 2>nul
git remote add origin https://github.com/Aniketkumar-01/socials_downloader.git
git branch -M main

echo.
echo Pushing to https://github.com/Aniketkumar-01/socials_downloader.git...
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo   SUCCESS! Repository pushed to GitHub.
    echo ============================================================
) else (
    echo.
    echo ============================================================
    echo   Note: If prompted, authenticate with your GitHub account
    echo   or Personal Access Token (PAT).
    echo ============================================================
)

echo.
pause
