# OmniDownloader - PowerShell Git Push & Release Publisher
param (
    [string]$Version = "v1.2.9",
    [string]$Message = "feat(release): v1.2.9 - pause/resume downloads, batch multi-url downloads, playlist numbering, and UI version pill"
)

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Publishing OmniDownloader $Version Release to GitHub" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Clean up obsolete scratch, temporary caches, and sensitive files
Write-Host "[1/4] Cleaning obsolete scratch, temporary caches, and sensitive files..." -ForegroundColor Yellow
& "$ScriptDir\clean_repo.ps1" -Silent

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
