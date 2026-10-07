@echo off
echo ============================================================
echo   Publishing OmniDownloader v1.3.0 Release to GitHub
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/4] Cleaning obsolete scratch, temporary caches, and sensitive files...
call clean_repo.bat --silent 2>nul

echo [2/4] Committing latest updates to main...
git add -A
git commit -m "feat(release): v1.3.0 - fix fetch info and paste button, add batch mode platform detection, and remove watchdog timeout"
git push origin main

echo.
echo [3/4] Tagging release v1.3.0...
git tag -a v1.3.0 -m "OmniDownloader v1.3.0 - Production Release" -f

echo.
echo [4/4] Pushing tag v1.3.0 to GitHub...
git push origin v1.3.0 --force

echo.
echo ============================================================
echo   SUCCESS! Release v1.3.0 is now building on GitHub Actions!
echo   
echo   Watch both OmniDownloader-Setup.exe and OmniDownloader.exe
echo   compile live at:
echo   https://github.com/Aniketkumar-01/socials_downloader/actions
echo ============================================================
echo.
pause
