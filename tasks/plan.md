# Implementation Plan: OmniDownloader Windows Installer (Setup.exe)

## Overview
Transform OmniDownloader from a standalone portable executable into a first-class installed Windows application (`OmniDownloader-Setup.exe`) that installs into the user profile, integrates with the Windows Start Menu and Search bar, creates desktop shortcuts, and registers with Windows Settings (Add/Remove Programs) for clean uninstallation.

---

## Architectural Decisions

1. **Installer Engine: Inno Setup 6**
   - **Rationale:** Inno Setup is the de facto standard for open-source Windows installers (used by VS Code, Git for Windows, Notepad++). It creates small, clean, high-performance installer `.exe` files and has native support in GitHub Actions via Chocolatey / standard runners.
   - **No-Admin Required (Per-User Install Mode):** Configured with `PrivilegesRequired=lowest` targeting `%LOCALAPPDATA%\Programs\OmniDownloader`. Users do not need Administrator privileges or UAC elevation to install.

2. **Dual Distribution Model (Best of Both Worlds):**
   - **`OmniDownloader-Setup.exe` (Installer - Default):** Installs app, creates Start Menu shortcut (searchable via Windows Search), creates Desktop shortcut, registers in Windows Settings.
   - **`OmniDownloader-Portable.exe` (Standalone):** Remains available for users who prefer a single standalone file on USB drives or temporary workstations.

3. **Application Icon & Assets:**
   - Embed a high-resolution multi-size `.ico` (16x16, 32x32, 48x48, 64x64, 128x128, 256x256) into both the standalone executable and the setup wizard.

4. **CI/CD Automation via GitHub Actions:**
   - Extend `.github/workflows/release.yml` to compile the Inno Setup script after building PyInstaller and publish both `OmniDownloader-Setup.exe` and `OmniDownloader-Portable.exe` to GitHub Releases.

---

## Advantages vs. Disadvantages

| Feature | Standalone Portable `.exe` (Current) | Installed Setup Wizard (`Setup.exe`) |
| :--- | :--- | :--- |
| **Windows Search Bar** | ❌ Cannot find by typing in Start Menu | ✅ Instantly searchable via `Win` + "Omni" |
| **Start Menu / Pin to Taskbar** | ❌ Manual pinning awkward | ✅ Automatically added to Start Menu |
| **Desktop Shortcut** | ❌ User must manually create shortcut | ✅ Created automatically on install |
| **Install Location** | Wherever downloaded (e.g. `Downloads/`) | Standard `%LOCALAPPDATA%\Programs\OmniDownloader` |
| **Permissions Needed** | None | None (Per-user install, no UAC prompt) |
| **Clean Uninstall** | Delete file manually (leaves appdata) | Windows Settings > Installed Apps > Uninstall |
| **Portability** | High (runs from USB drive) | Requires installation on machine |

---

## Task Breakdown

### Phase 1: Application Assets & Inno Setup Script
- [ ] **Task 1: Generate High-Resolution Application Icon (`app.ico`)**
  - Create a modern multi-size Windows icon file (`assets/app.ico`) containing 256x256, 128x128, 64x64, 48x48, 32x32, 16x16 formats.
  - Link icon in `omnidownloader.spec` so the executable displays the custom icon in File Explorer.
- [ ] **Task 2: Create Inno Setup Configuration Script (`installer.iss`)**
  - Define application metadata (AppId, AppName, Version, Publisher, URL).
  - Configure target path: `{localappdata}\Programs\OmniDownloader`.
  - Configure Start Menu shortcut `{autoprograms}\OmniDownloader.lnk` with search tags.
  - Configure optional Desktop shortcut `{autodesktop}\OmniDownloader.lnk`.
  - Include automatic uninstaller with Windows Registry display properties (DisplayIcon, Publisher, DisplayVersion).
  - Add post-install "Launch OmniDownloader" checkbox.

### Phase 2: Local Build & CI Automation
- [ ] **Task 3: Local Build Script Integration (`build_installer.bat`)**
  - Create a local batch script that compiles PyInstaller and runs Inno Setup compiler (`ISCC.exe`) if installed.
- [ ] **Task 4: GitHub Actions Workflow Integration (`.github/workflows/release.yml`)**
  - Add step to install Inno Setup on Windows runner (`choco install innosetup --no-progress`).
  - Run `iscc.exe installer.iss` after `pyinstaller` completes.
  - Upload both `OmniDownloader-Setup.exe` and `OmniDownloader-Portable.exe` to GitHub Releases.

### Phase 3: Documentation & Release Preparation
- [ ] **Task 5: Update Documentation & Release Scripts**
  - Update `README.md` and release notes with installation guide.
  - Update `publish_release.bat` to publish the new installer version.

---

## Verification Plan
1. Compile executable and build installer using Inno Setup.
2. Run installer on clean Windows environment:
   - Verify files install to `%LOCALAPPDATA%\Programs\OmniDownloader`.
   - Verify Windows Start Menu has "OmniDownloader".
   - Press Windows Key, type "OmniDownloader", verify app appears as top result.
   - Verify desktop shortcut launches application correctly.
3. Open Windows Settings > Apps > Installed apps:
   - Verify OmniDownloader appears with icon, version, and publisher.
   - Click "Uninstall" and verify all files, registry keys, and shortcuts are cleanly removed.
