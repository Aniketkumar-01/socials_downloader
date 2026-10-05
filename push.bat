@echo off
echo ============================================================
echo   OmniDownloader - Quick Git Push to main
echo ============================================================
echo.

cd /d "%~dp0"

echo Staging all changes...
git add -A

echo Committing...
git commit -m "fix(windows): resolve WinError 448 untrusted mount point in system PATH during media extraction"

echo Pushing to origin main...
git push origin main

echo.
echo ============================================================
echo   Sync complete!
echo ============================================================
echo.
pause
