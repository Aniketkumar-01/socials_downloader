# OmniDownloader - Unified Release Publisher
param (
    [string]$Version = "v1.3.0",
    [string]$Message = "chore(release): v1.3.0 - security hardening, clean packaging, and architecture cleanup"
)

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Publishing OmniDownloader $Version Release to GitHub" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Clean up obsolete scratch and temporary files if any remain
Write-Host "[1/4] Cleaning obsolete scratch files..." -ForegroundColor Yellow
$obsoletePaths = @(
    "$RepoRoot\tasks",
    "$RepoRoot\DESIGN.md",
    "$RepoRoot\PRODUCT.md",
    "$RepoRoot\desktop.py",
    "$RepoRoot\push.bat",
    "$RepoRoot\push.ps1",
    "$RepoRoot\push_to_github.bat",
    "$RepoRoot\publish_release.bat",
    "$RepoRoot\publish_release.ps1",
    "$RepoRoot\OmniDownloader.bat",
    "$RepoRoot\OmniDownloader.vbs",
    "$RepoRoot\create_desktop_shortcut.vbs",
    "$RepoRoot\start.bat",
    "$RepoRoot\build_exe.bat",
    "$RepoRoot\build_installer.bat",
    "$RepoRoot\create_icon.py",
    "$RepoRoot\cookies.txt.example"
)
foreach ($p in $obsoletePaths) {
    if (Test-Path $p) {
        git rm -rf --cached $p 2>$null
        Remove-Item -Recurse -Force $p -ErrorAction SilentlyContinue
    }
}

# 2. Stage and Commit
Write-Host "[2/4] Committing latest changes to main..." -ForegroundColor Yellow
$gitDiff = git status --porcelain
if ($gitDiff) {
    git add -A
    git commit -m "$Message"
} else {
    Write-Host "  Working tree clean, no new changes to commit."
}
git push origin main

# 3. Tag Release
Write-Host ""
Write-Host "[3/4] Tagging release $Version..." -ForegroundColor Yellow
git tag -a $Version -m "OmniDownloader $Version" -f

# 4. Push Tag
Write-Host ""
Write-Host "[4/4] Pushing tag $Version to GitHub..." -ForegroundColor Yellow
git push origin $Version --force

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  SUCCESS! Release $Version is now building on GitHub Actions!" -ForegroundColor Green
Write-Host "  " -ForegroundColor Green
Write-Host "  Watch release builds compile live at:" -ForegroundColor Green
Write-Host "  https://github.com/Aniketkumar-01/socials_downloader/actions" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
