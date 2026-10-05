# OmniDownloader - PowerShell Git Push & Release Publisher
$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Publishing OmniDownloader v1.2.3 Release to GitHub" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Clean up obsolete scratch and internal development files
Write-Host "[1/4] Cleaning obsolete scratch and internal development files..." -ForegroundColor Yellow
git rm -rf --cached tasks DESIGN.md PRODUCT.md desktop.py 2>$null
if (Test-Path "$ScriptDir\tasks") { Remove-Item -Recurse -Force "$ScriptDir\tasks" -ErrorAction SilentlyContinue }
if (Test-Path "$ScriptDir\DESIGN.md") { Remove-Item -Force "$ScriptDir\DESIGN.md" -ErrorAction SilentlyContinue }
if (Test-Path "$ScriptDir\PRODUCT.md") { Remove-Item -Force "$ScriptDir\PRODUCT.md" -ErrorAction SilentlyContinue }
if (Test-Path "$ScriptDir\desktop.py") { Remove-Item -Force "$ScriptDir\desktop.py" -ErrorAction SilentlyContinue }

# 2. Stage and Commit
Write-Host "[2/4] Committing latest updates to main..." -ForegroundColor Yellow
git add -A
git commit -m "feat(release): v1.2.3 - production security hardening, universal media engine, and clean packaging"
git push origin main

# 3. Tag Release v1.2.3
Write-Host ""
Write-Host "[3/4] Tagging release v1.2.3..." -ForegroundColor Yellow
git tag -a v1.2.3 -m "OmniDownloader v1.2.3 - Security Hardening, Clean Packaging & Universal Media Engine" -f

# 4. Push Tag
Write-Host ""
Write-Host "[4/4] Pushing tag v1.2.3 to GitHub..." -ForegroundColor Yellow
git push origin v1.2.3 --force

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  SUCCESS! Release v1.2.3 is now building on GitHub Actions!" -ForegroundColor Green
Write-Host "  " -ForegroundColor Green
Write-Host "  Watch both OmniDownloader-Setup.exe and OmniDownloader.exe" -ForegroundColor Green
Write-Host "  compile live at:" -ForegroundColor Green
Write-Host "  https://github.com/Aniketkumar-01/socials_downloader/actions" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
