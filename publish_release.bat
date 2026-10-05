@echo off
echo ============================================================
echo   Publishing OmniDownloader v1.1.2 Release to GitHub
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/3] Committing latest updates to main...
git add -A
git commit -m "fix(uvicorn): pass log_config=None to bypass dictConfig formatter crash" 2>nul
git push origin main

echo.
echo [2/3] Tagging release v1.1.2...
git tag -a v1.1.2 -m "OmniDownloader v1.1.2 - Fixed Uvicorn dictConfig default formatter startup crash" -f

echo.
echo [3/3] Pushing tag v1.1.2 to GitHub...
git push origin v1.1.2 --force

echo.
echo ============================================================
echo   SUCCESS! Release v1.1.2 is now building on GitHub Actions!
echo   
echo   Watch your standalone .exe compile live at:
echo   https://github.com/Aniketkumar-01/socials_downloader/actions
echo ============================================================
echo.
pause
