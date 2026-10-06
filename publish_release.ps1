# OmniDownloader - PowerShell Git Push & Release Publisher
param (
    [string]$Version = "v1.2.6",
    [string]$Message = "feat(release): v1.2.6 - in-app update system, process watchdog, and clean uninstaller"
)

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Publishing OmniDownloader $Version Release to GitHub" -ForegroundColor Cyan
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
$status = git status --porcelain
if ($status) {
    git commit -m "$Message"
} else {
    Write-Host "  Working tree clean, no new changes to commit."
}
git push origin main

# 3. Tag Release
Write-Host ""
Write-Host "[3/4] Tagging release $Version..." -ForegroundColor Yellow
git tag -a $Version -m "OmniDownloader $Version - Production Release" -f

# 4. Push Tag
Write-Host ""
Write-Host "[4/4] Pushing tag $Version to GitHub..." -ForegroundColor Yellow
git push origin $Version --force

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  SUCCESS! Release $Version is now building on GitHub Actions!" -ForegroundColor Green
Write-Host "  " -ForegroundColor Green
Write-Host "  Watch both OmniDownloader-Setup.exe and OmniDownloader.exe" -ForegroundColor Green
Write-Host "  compile live at:" -ForegroundColor Green
Write-Host "  https://github.com/Aniketkumar-01/socials_downloader/actions" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
