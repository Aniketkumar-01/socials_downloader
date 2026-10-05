@echo off
echo ============================================================
echo   Publishing OmniDownloader v1.2.3 Release to GitHub
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/4] Cleaning obsolete scratch and internal development files...
git rm -rf --cached tasks DESIGN.md PRODUCT.md desktop.py 2>nul
if exist "tasks" rd /s /q "tasks" 2>nul
if exist "DESIGN.md" del /f /q "DESIGN.md" 2>nul
if exist "PRODUCT.md" del /f /q "PRODUCT.md" 2>nul
if exist "desktop.py" del /f /q "desktop.py" 2>nul

echo [2/4] Committing latest updates to main...
git add -A
git commit -m "feat(release): v1.2.3 - production security hardening, universal media engine, and clean packaging"
git push origin main

echo.
echo [3/4] Tagging release v1.2.3...
git tag -a v1.2.3 -m "OmniDownloader v1.2.3 - Security Hardening, Clean Packaging & Universal Media Engine" -f

echo.
echo [4/4] Pushing tag v1.2.3 to GitHub...
git push origin v1.2.3 --force

echo.
echo ============================================================
echo   SUCCESS! Release v1.2.3 is now building on GitHub Actions!
echo   
echo   Watch both OmniDownloader-Setup.exe and OmniDownloader.exe
echo   compile live at:
echo   https://github.com/Aniketkumar-01/socials_downloader/actions
echo ============================================================
echo.
pause
