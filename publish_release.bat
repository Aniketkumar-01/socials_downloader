@echo off
echo ============================================================
echo   Publishing OmniDownloader v1.1.1 Release to GitHub
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/3] Committing latest updates to main...
git add -A
git commit -m "fix(launcher): resolve startup crash, missing uvicorn hooks, and browser app shell" 2>nul
git push origin main

echo.
echo [2/3] Tagging release v1.1.1...
git tag -a v1.1.1 -m "OmniDownloader v1.1.1 - Fixed standalone launcher and silent startup crash" -f

echo.
echo [3/3] Pushing tag v1.1.1 to GitHub...
git push origin v1.1.1 --force

echo.
echo ============================================================
echo   SUCCESS! Release v1.1.1 is now building on GitHub Actions!
echo   
echo   Watch your standalone .exe compile live at:
echo   https://github.com/Aniketkumar-01/socials_downloader/actions
echo ============================================================
echo.
pause
