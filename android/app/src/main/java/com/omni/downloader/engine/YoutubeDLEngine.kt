package com.omni.downloader.engine

import android.content.Context
import android.util.Log
import com.omni.downloader.data.models.MediaMetadata
import com.omni.downloader.data.models.PlaylistItem
import com.omni.downloader.data.models.QualityOption
import com.yausername.youtubedl_android.YoutubeDL
import com.yausername.youtubedl_android.YoutubeDLRequest
import com.yausername.youtubedl_android.mapper.VideoInfo
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

object YoutubeDLEngine {
    private const val TAG = "YoutubeDLEngine"

    /**
     * Extracts video and playlist metadata without downloading media.
     */
    suspend fun fetchMetadata(context: Context, url: String): Result<MediaMetadata> = withContext(Dispatchers.IO) {
        try {
            val request = YoutubeDLRequest(url).apply {
                addOption("--skip-download")
                addOption("--flat-playlist")
                addOption("--no-warnings")
                val cookiesFile = StorageHelper.getAppCookiesFile(context)
                if (cookiesFile.exists() && cookiesFile.length() > 0) {
                    addOption("--cookies", cookiesFile.absolutePath)
                }
            }

            val videoInfo: VideoInfo = YoutubeDL.getInstance().getInfo(request)
            val title = videoInfo.title ?: "Untitled Media"
            val channel = videoInfo.uploader ?: "Unknown Creator"
            val durationSecs = videoInfo.duration
            val durationFormatted = if (durationSecs > 0) {
                val mins = durationSecs / 60
                val secs = durationSecs % 60
                String.format("%02d:%02d", mins, secs)
            } else null

            val isPlaylist = videoInfo.entries != null && videoInfo.entries.isNotEmpty()
            val playlistItems = if (isPlaylist) {
                videoInfo.entries.mapIndexed { index, entry ->
                    PlaylistItem(
                        id = entry.id ?: "$index",
                        title = entry.title ?: "Item ${index + 1}",
                        url = entry.url ?: url,
                        thumbnail = entry.thumbnail,
                        isSelected = true
                    )
                }
            } else {
                emptyList()
            }

            val platform = when {
                url.contains("youtube.com", true) || url.contains("youtu.be", true) -> "YouTube"
                url.contains("instagram.com", true) -> "Instagram"
                url.contains("tiktok.com", true) -> "TikTok"
                url.contains("twitter.com", true) || url.contains("x.com", true) -> "X (Twitter)"
                url.contains("bilibili.com", true) -> "Bilibili"
                url.contains("facebook.com", true) -> "Facebook"
                url.contains("reddit.com", true) -> "Reddit"
                else -> "Universal"
            }

            val qualities = listOf(
                QualityOption("best", "Best Available", "Source Maximum", false),
                QualityOption("1080p", "Full HD 1080p", "1080p", false),
                QualityOption("720p", "HD 720p", "720p", false),
                QualityOption("480p", "Standard 480p", "480p", false),
                QualityOption("audio_mp3", "Audio Only (MP3)", "MP3 192kbps", true)
            )

            Result.success(
                MediaMetadata(
                    url = url,
                    title = title,
                    channel = channel,
                    durationFormatted = durationFormatted,
                    thumbnail = videoInfo.thumbnail,
                    platform = platform,
                    isPlaylist = isPlaylist,
                    playlistItems = playlistItems,
                    availableQualities = qualities
                )
            )
        } catch (e: Exception) {
            Log.e(TAG, "Extraction error: ${e.message}", e)
            Result.failure(e)
        }
    }

    /**
     * Executes the download with real-time progress callbacks.
     */
    suspend fun executeDownload(
        context: Context,
        url: String,
        qualityId: String,
        targetDir: File,
        onProgress: (progress: Float, etaInSeconds: Long, line: String) -> Unit
    ): Result<File> = withContext(Dispatchers.IO) {
        try {
            val request = YoutubeDLRequest(url).apply {
                addOption("-o", "${targetDir.absolutePath}/%(title).100B [%(id)s].%(ext)s")
                addOption("--no-mtime")
                addOption("--windows-filenames")

                val cookiesFile = StorageHelper.getAppCookiesFile(context)
                if (cookiesFile.exists() && cookiesFile.length() > 0) {
                    addOption("--cookies", cookiesFile.absolutePath)
                }

                when (qualityId) {
                    "audio_mp3" -> {
                        addOption("-x")
                        addOption("--audio-format", "mp3")
                        addOption("--audio-quality", "192K")
                    }
                    "1080p" -> {
                        addOption("-f", "bestvideo[height<=?1080]+bestaudio/best[height<=?1080]/best")
                        addOption("--merge-output-format", "mp4")
                    }
                    "720p" -> {
                        addOption("-f", "bestvideo[height<=?720]+bestaudio/best[height<=?720]/best")
                        addOption("--merge-output-format", "mp4")
                    }
                    "480p" -> {
                        addOption("-f", "bestvideo[height<=?480]+bestaudio/best[height<=?480]/best")
                        addOption("--merge-output-format", "mp4")
                    }
                    else -> {
                        addOption("-f", "bestvideo+bestaudio/best")
                        addOption("--merge-output-format", "mp4")
                    }
                }
            }

            YoutubeDL.getInstance().execute(request) { progress, eta, line ->
                onProgress(progress, eta, line ?: "")
            }

            // Find the downloaded file in targetDir
            val downloadedFiles = targetDir.listFiles { file ->
                val name = file.name.lowercase()
                file.isFile && (name.endsWith(".mp4") || name.endsWith(".mp3") || name.endsWith(".mkv") || name.endsWith(".m4a"))
            }?.sortedByDescending { it.lastModified() }

            val completedFile = downloadedFiles?.firstOrNull()
                ?: throw IllegalStateException("Download finished but target media file not found on disk.")

            Result.success(completedFile)
        } catch (e: Exception) {
            Log.e(TAG, "Download execution failed: ${e.message}", e)
            Result.failure(e)
        }
    }
}
