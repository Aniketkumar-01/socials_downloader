package com.omni.downloader.engine

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import android.util.Log
import androidx.core.content.FileProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.BufferedReader
import java.io.File
import java.io.FileOutputStream
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL

data class AppUpdateInfo(
    val isUpdateAvailable: Boolean,
    val currentVersion: String,
    val latestVersion: String,
    val releaseTitle: String,
    val releaseNotes: String,
    val apkDownloadUrl: String?
)

object UpdateManager {
    private const val TAG = "UpdateManager"
    const val CURRENT_APP_VERSION = "1.4.3"
    private const val GITHUB_API_URL = "https://api.github.com/repos/Aniketkumar-01/socials_downloader/releases/latest"

    suspend fun checkForUpdates(): Result<AppUpdateInfo> = withContext(Dispatchers.IO) {
        try {
            val url = URL(GITHUB_API_URL)
            val connection = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                connectTimeout = 8000
                readTimeout = 8000
                setRequestProperty("Accept", "application/vnd.github.v3+json")
                setRequestProperty("User-Agent", "OmniDownloader-Android-Client")
            }

            if (connection.responseCode != HttpURLConnection.HTTP_OK) {
                return@withContext Result.failure(Exception("GitHub API returned HTTP ${connection.responseCode}"))
            }

            val reader = BufferedReader(InputStreamReader(connection.inputStream))
            val response = reader.readText()
            reader.close()

            val json = JSONObject(response)
            val tagName = json.optString("tag_name", "").removePrefix("v").removePrefix("android-v").trim()
            val releaseTitle = json.optString("name", "New OmniDownloader Release")
            val releaseNotes = json.optString("body", "Bug fixes and performance improvements.")

            var apkUrl: String? = null
            val assets = json.optJSONArray("assets")
            if (assets != null) {
                for (i in 0 until assets.length()) {
                    val asset = assets.getJSONObject(i)
                    val name = asset.optString("name", "")
                    if (name.endsWith(".apk", ignoreCase = true)) {
                        apkUrl = asset.optString("browser_download_url")
                        break
                    }
                }
            }

            // Only mark update available if an APK actually exists in the release
            val isAvailable = isVersionNewer(tagName, CURRENT_APP_VERSION) && !apkUrl.isNullOrBlank()

            Result.success(
                AppUpdateInfo(
                    isUpdateAvailable = isAvailable,
                    currentVersion = CURRENT_APP_VERSION,
                    latestVersion = tagName,
                    releaseTitle = releaseTitle,
                    releaseNotes = releaseNotes,
                    apkDownloadUrl = apkUrl
                )
            )
        } catch (e: Exception) {
            Log.e(TAG, "Update check failed: ${e.message}", e)
            Result.failure(e)
        }
    }

    /**
     * Downloads the APK update file directly in the app with progress updates,
     * saving it to the app's cache directory ready for installation.
     */
    suspend fun downloadApk(
        context: Context,
        apkUrl: String,
        onProgress: (bytesRead: Long, totalBytes: Long, percent: Int) -> Unit
    ): Result<File> = withContext(Dispatchers.IO) {
        try {
            var currentUrl = apkUrl
            var connection: HttpURLConnection
            var redirects = 0

            // Follow HTTP redirects manually (GitHub releases redirect to AWS S3 CDN)
            while (true) {
                connection = (URL(currentUrl).openConnection() as HttpURLConnection).apply {
                    instanceFollowRedirects = true
                    connectTimeout = 15000
                    readTimeout = 30000
                    setRequestProperty("User-Agent", "OmniDownloader-Android-Client")
                }

                val code = connection.responseCode
                if (code in 300..399 && redirects < 5) {
                    val loc = connection.getHeaderField("Location")
                    connection.disconnect()
                    if (loc != null) {
                        currentUrl = loc
                        redirects++
                        continue
                    }
                }
                break
            }

            if (connection.responseCode != HttpURLConnection.HTTP_OK) {
                return@withContext Result.failure(Exception("Failed to download APK: HTTP ${connection.responseCode}"))
            }

            val totalBytes = connection.contentLengthLong
            val updateDir = File(context.cacheDir, "updates").apply { if (!exists()) mkdirs() }
            val apkFile = File(updateDir, "omnidownloader-update.apk")
            if (apkFile.exists()) apkFile.delete()

            connection.inputStream.use { input ->
                FileOutputStream(apkFile).use { output ->
                    val buffer = ByteArray(64 * 1024)
                    var bytesReadTotal = 0L
                    var read: Int
                    var lastReport = 0L

                    while (input.read(buffer).also { read = it } != -1) {
                        output.write(buffer, 0, read)
                        bytesReadTotal += read
                        val now = System.currentTimeMillis()
                        if (now - lastReport > 200 || bytesReadTotal == totalBytes) {
                            lastReport = now
                            val percent = if (totalBytes > 0) ((bytesReadTotal * 100) / totalBytes).toInt() else -1
                            onProgress(bytesReadTotal, totalBytes, percent)
                        }
                    }
                    output.flush()
                }
            }
            connection.disconnect()

            if (!apkFile.exists() || apkFile.length() <= 0) {
                return@withContext Result.failure(Exception("Downloaded update file is empty or corrupted."))
            }

            Result.success(apkFile)
        } catch (e: Exception) {
            Log.e(TAG, "APK download error: ${e.message}", e)
            Result.failure(e)
        }
    }

    /**
     * Triggers the Android package installer prompt using FileProvider.
     */
    fun installApk(context: Context, apkFile: File): Result<Unit> {
        return try {
            if (!apkFile.exists()) {
                return Result.failure(Exception("APK file not found: ${apkFile.absolutePath}"))
            }

            // On Android 8.0+, check if installing from unknown sources is allowed
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                if (!context.packageManager.canRequestPackageInstalls()) {
                    val manageIntent = Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES).apply {
                        data = Uri.parse("package:${context.packageName}")
                        flags = Intent.FLAG_ACTIVITY_NEW_TASK
                    }
                    context.startActivity(manageIntent)
                }
            }

            val contentUri = FileProvider.getUriForFile(
                context,
                "${context.packageName}.provider",
                apkFile
            )

            val installIntent = Intent(Intent.ACTION_VIEW).apply {
                setDataAndType(contentUri, "application/vnd.android.package-archive")
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_GRANT_READ_URI_PERMISSION
            }
            context.startActivity(installIntent)
            Result.success(Unit)
        } catch (e: Exception) {
            Log.e(TAG, "Launch APK install failed: ${e.message}", e)
            // Fallback to opening browser release page if install intent fails
            openDownloadUrl(context, "https://github.com/Aniketkumar-01/socials_downloader/releases/latest")
            Result.failure(e)
        }
    }

    fun openDownloadUrl(context: Context, downloadUrl: String) {
        try {
            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(downloadUrl)).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            }
            context.startActivity(intent)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to launch browser download: ${e.message}")
        }
    }

    private fun isVersionNewer(latest: String, current: String): Boolean {
        try {
            val latestParts = latest.split(".").mapNotNull { it.filter { char -> char.isDigit() }.toIntOrNull() }
            val currentParts = current.split(".").mapNotNull { it.filter { char -> char.isDigit() }.toIntOrNull() }

            val maxLen = maxOf(latestParts.size, currentParts.size)
            for (i in 0 until maxLen) {
                val l = latestParts.getOrElse(i) { 0 }
                val c = currentParts.getOrElse(i) { 0 }
                if (l > c) return true
                if (l < c) return false
            }
        } catch (e: Exception) {
            return latest != current
        }
        return false
    }
}
