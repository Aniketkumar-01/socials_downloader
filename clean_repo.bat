@echo off
setlocal
cd /d "%~dp0"

if not "%1"=="--silent" (
    echo ============================================================
    echo   OmniDownloader - Repository Cleanup Utility
    echo ============================================================
    echo.
    echo Cleaning unnecessary files, temporary caches, and scratch data...
)

:: 1. Remove sensitive session credentials (keep cookies.txt.example template only)
if exist "cookies.txt" (
    del /f /q "cookies.txt" 2>nul
    git rm -f --cached "cookies.txt" 2>nul
)

:: 2. Remove internal development specifications and scratch notes
if exist "SPEC-app-updater.md" (
    del /f /q "SPEC-app-updater.md" 2>nul
    git rm -f --cached "SPEC-app-updater.md" 2>nul
)
if exist "SPEC.md" (
    del /f /q "SPEC.md" 2>nul
    git rm -f --cached "SPEC.md" 2>nul
)
if exist "ARCHITECTURE.md" (
    del /f /q "ARCHITECTURE.md" 2>nul
    git rm -f --cached "ARCHITECTURE.md" 2>nul
)
if exist "DESIGN.md" (
    del /f /q "DESIGN.md" 2>nul
    git rm -f --cached "DESIGN.md" 2>nul
)
if exist "PRODUCT.md" (
    del /f /q "PRODUCT.md" 2>nul
    git rm -f --cached "PRODUCT.md" 2>nul
)
if exist "iterations_done.md" (
    del /f /q "iterations_done.md" 2>nul
    git rm -f --cached "iterations_done.md" 2>nul
)
if exist "desktop.py" (
    del /f /q "desktop.py" 2>nul
    git rm -f --cached "desktop.py" 2>nul
)
if exist "backend\tests\run_1000_iterations.py" (
    del /f /q "backend\tests\run_1000_iterations.py" 2>nul
    git rm -f --cached "backend\tests\run_1000_iterations.py" 2>nul
)

:: 3. Remove obsolete duplicate push scripts
if exist "push.bat" (
    del /f /q "push.bat" 2>nul
    git rm -f --cached "push.bat" 2>nul
)
if exist "push.ps1" (
    del /f /q "push.ps1" 2>nul
    git rm -f --cached "push.ps1" 2>nul
)
if exist "push_to_github.bat" (
    del /f /q "push_to_github.bat" 2>nul
    git rm -f --cached "push_to_github.bat" 2>nul
)

:: 4. Remove internal task directories
if exist "tasks" (
    rd /s /q "tasks" 2>nul
    git rm -rf --cached "tasks" 2>nul
)

:: 5. Remove agent and tooling scratch directories
if exist ".impeccable" rd /s /q ".impeccable" 2>nul
if exist ".opencode" rd /s /q ".opencode" 2>nul

:: 6. Remove Python and test caches
if exist ".pytest_cache" rd /s /q ".pytest_cache" 2>nul
if exist "backend\.pytest_cache" rd /s /q "backend\.pytest_cache" 2>nul
if exist "__pycache__" rd /s /q "__pycache__" 2>nul
if exist "backend\app\__pycache__" rd /s /q "backend\app\__pycache__" 2>nul
if exist "backend\tests\__pycache__" rd /s /q "backend\tests\__pycache__" 2>nul

for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
del /s /f /q *.pyc *.pyo *.pyd 2>nul

:: 7. Remove OS metadata artifacts
del /s /f /q .DS_Store Thumbs.db desktop.ini 2>nul

if not "%1"=="--silent" (
    echo.
    echo ============================================================
    echo   Repository successfully cleaned!
    echo ============================================================
    echo.
    pause
)
exit /b 0
