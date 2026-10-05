@echo off
setlocal
title OmniDownloader PC App
cd /d "%~dp0"

:: 1. Check Python
if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
) else (
    where python >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] Python was not found. Please run start.bat first to set up the environment.
        pause
        exit /b 1
    )
    set "PYTHON_EXE=python"
)

:: 2. Launch Desktop Application
echo Starting OmniDownloader Windows Application...
"%PYTHON_EXE%" desktop.py

exit /b 0
