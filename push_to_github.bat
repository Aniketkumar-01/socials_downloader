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

echo [3/5] Cleaning obsolete files and staging (.gitignore protects sensitive data)...
git rm -rf --cached tasks DESIGN.md PRODUCT.md desktop.py 2>nul
if exist "tasks" rd /s /q "tasks" 2>nul
if exist "DESIGN.md" del /f /q "DESIGN.md" 2>nul
if exist "PRODUCT.md" del /f /q "PRODUCT.md" 2>nul
if exist "desktop.py" del /f /q "desktop.py" 2>nul

git add -A

echo [4/5] Creating commit...
git commit -m "feat(release): v1.2.3 - production security hardening, universal media engine, and clean packaging"

echo [5/5] Setting remote and pushing to GitHub...
git remote remove origin 2>nul
git remote add origin https://github.com/Aniketkumar-01/socials_downloader.git
git branch -M main

echo.
echo Pushing code to main branch...
git push -u origin main

echo.
set /p CREATE_RELEASE="Do you want to create and push a v1.2.3 release tag to compile Windows binaries on GitHub? (y/n): "
if /i "%CREATE_RELEASE%"=="y" (
    echo.
    echo Tagging release v1.2.3...
    git tag -a v1.2.3 -m "OmniDownloader v1.2.3 - Security Hardening, Clean Packaging & Universal Media Engine" -f 2>nul
    echo Pushing tag to GitHub to trigger automated build...
    git push origin v1.2.3 --force
    echo.
    echo GitHub Actions is now compiling OmniDownloader-Setup.exe and OmniDownloader.exe!
    echo Visit: https://github.com/Aniketkumar-01/socials_downloader/actions
)

echo.
echo ============================================================
echo   Repository synced with GitHub!
echo ============================================================
echo.
pause
