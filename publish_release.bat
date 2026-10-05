@echo off
echo ============================================================
echo   Publishing OmniDownloader v1.2.1 Release to GitHub
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/3] Committing latest updates to main...
git add -A
git commit -m "fix(windows): resolve WinError 448 untrusted mount point in system PATH during media extraction"
git push origin main

echo.
echo [2/3] Tagging release v1.2.1...
git tag -a v1.2.1 -m "OmniDownloader v1.2.1 - Windows Mount Point & PATH Hardening (WinError 448 Fix)" -f

echo.
echo [3/3] Pushing tag v1.2.1 to GitHub...
git push origin v1.2.1 --force

echo.
echo ============================================================
echo   SUCCESS! Release v1.2.1 is now building on GitHub Actions!
echo   
echo   Watch both OmniDownloader-Setup.exe and OmniDownloader.exe
echo   compile live at:
echo   https://github.com/Aniketkumar-01/socials_downloader/actions
echo ============================================================
echo.
pause
