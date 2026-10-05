@echo off
echo ============================================================
echo   OmniDownloader - Git Setup, Push & Release Publisher
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

echo [3/5] Staging files (.gitignore protects cookies.txt, venv, and build artifacts)...
git add .

echo [4/5] Creating commit...
git commit -m "feat: standalone Windows exe packaging, automated GitHub releases, and prerequisites FFmpeg alert banner"

echo [5/5] Setting remote and pushing to GitHub...
git remote remove origin 2>nul
git remote add origin https://github.com/Aniketkumar-01/socials_downloader.git
git branch -M main

echo.
echo Pushing code to main branch...
git push -u origin main

echo.
set /p CREATE_RELEASE="Do you want to create and push a v1.0.0 release tag to build OmniDownloader.exe on GitHub? (y/n): "
if /i "%CREATE_RELEASE%"=="y" (
    echo.
    echo Tagging release v1.0.0...
    git tag -a v1.0.0 -m "OmniDownloader v1.0.0 Release" 2>nul
    echo Pushing tag to GitHub to trigger automated .exe build...
    git push origin v1.0.0 --force
    echo.
    echo GitHub Actions is now compiling OmniDownloader.exe!
    echo Visit: https://github.com/Aniketkumar-01/socials_downloader/actions
)

echo.
echo ============================================================
echo   Repository synced with GitHub!
echo ============================================================
echo.
pause
