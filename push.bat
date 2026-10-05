@echo off
echo ============================================================
echo   OmniDownloader - Quick Git Push to main
echo ============================================================
echo.

cd /d "%~dp0"

echo Staging all changes...
git add -A

echo Committing...
git commit -m "fix(quality): restore high-res stream extraction, dynamic quality tiers, and orientation-neutral size estimation"

echo Pushing to origin main...
git push origin main

echo.
echo ============================================================
echo   Sync complete!
echo ============================================================
echo.
pause
