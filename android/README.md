# 🤖 OmniDownloader for Android

**High-Performance Universal Video, Audio & Playlist Downloader for Android**

*Download videos, Reels, Shorts, and audio directly to your phone's Gallery, VLC, and Music library without needing a PC.*

---

## 🌟 Key Features on Mobile

- **📱 100% On-Device Processing**: Powered by `youtubedl-android` (embedded CPython + `yt-dlp` + FFmpeg NDK). Runs completely offline/standalone on your phone.
- **🔗 System Share Sheet Integration**: Tap **Share** inside YouTube, Instagram, or TikTok, select **OmniDownloader**, and the app instantly captures the URL and fetches formats.
- **🗂️ Scoped Storage & MediaStore**: Automatically saves completed `.mp4` into `Movies/OmniDownloader` (visible in Gallery / Google Photos) and `.mp3` into `Music/OmniDownloader` (visible in music players).
- **⚡ Foreground Service**: Downloads continue uninterrupted in the background even if the screen locks or you switch apps, with live progress in the Android notification tray.
- **🍪 In-App Cookie & Bot Bypass**: Log in to YouTube or Instagram inside the secure in-app WebView to extract cookies and bypass bot verification challenges.
- **🎨 Sleek Cyber-Obsidian UI**: Built with Jetpack Compose and Material 3, matching the desktop theme.

---

## 🛠️ Requirements & Setup

- **Android Studio**: Jellyfish (2023.3+) or Ladybug (2024.1+)
- **Android SDK**: Min SDK 24 (Android 7.0), Target SDK 34 (Android 14)
- **JDK**: Java 17+
- **NDK**: Included automatically via `youtubedl-android`

---

## 🚀 Building & Running

### Option A: Via Android Studio (Recommended)
1. Open **Android Studio**.
2. Select **Open** and choose the `android` folder in this repository (`d:\AG\yt\android`).
3. Allow Gradle to sync dependencies.
4. Connect an Android device (with USB debugging enabled) or start an Android Emulator.
5. Click the green **Run (▶)** button or press `Shift + F10`.

### Option B: Build APK via Terminal
```bash
cd android
./gradlew assembleDebug
```
The output APK will be located at:
`android/app/build/outputs/apk/debug/app-debug.apk`

To install directly to a connected phone:
```bash
./gradlew installDebug
```

---

## 📁 Architecture Overview

- `com.omni.downloader.OmniApplication`: Initializes embedded `YoutubeDL` & `FFmpeg` engines and notification channels.
- `com.omni.downloader.MainActivity`: Entry point, handles `ACTION_SEND` (Share Target from other apps) and Android 13+ notification permissions.
- `com.omni.downloader.engine.YoutubeDLEngine`: Manages metadata extraction and download command options.
- `com.omni.downloader.engine.StorageHelper`: Handles Scoped Storage and publishes completed files into Android's `MediaStore`.
- `com.omni.downloader.service.DownloadForegroundService`: Uninterrupted background download service with persistent notifications.
- `com.omni.downloader.ui.screens.MainScreen`: Jetpack Compose main UI.
- `com.omni.downloader.ui.screens.WebViewAuthActivity`: In-app authentication & cookie extractor.
