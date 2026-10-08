package com.omni.downloader.engine

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.BufferedReader
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
    const val CURRENT_APP_VERSION = "1.4.2"
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
