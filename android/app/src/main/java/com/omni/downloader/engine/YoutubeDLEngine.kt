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
import java.util.Locale

object YoutubeDLEngine {
    private const val TAG = "YoutubeDLEngine"

    private fun ensureInitialized(context: Context) {
        try {
            YoutubeDL.getInstance().init(context.applicationContext)
            com.yausername.ffmpeg.FFmpeg.getInstance().init(context.applicationContext)
        } catch (e: Exception) {
            Log.w(TAG, "Engine init check: ${e.message}")
        }
    }

    private fun formatSizeBytes(bytes: Long): String {
        if (bytes <= 0) return ""
        val b = bytes.toDouble()
        return when {
            b >= 1024 * 1024 * 1024 -> String.format(Locale.US, "%.1f GB", b / (1024 * 1024 * 1024))
            b >= 1024 * 1024 -> String.format(Locale.US, "%.1f MB", b / (1024 * 1024))
            b >= 1024 -> String.format(Locale.US, "%.0f KB", b / 1024)
            else -> String.format(Locale.US, "%.0f B", b)
        }
    }

    private fun estimateSize(durationSecs: Int, kbps: Int): String? {
        if (durationSecs <= 0) return null
        val bytes = (kbps.toLong() * 1000L / 8L) * durationSecs.toLong()
        return "~${formatSizeBytes(bytes)}"
    }

    /**
     * Updates the embedded yt-dlp core to the latest upstream release.
     */
    suspend fun updateYtDlpCore(context: Context): Result<String> = withContext(Dispatchers.IO) {
        try {
            ensureInitialized(context)
            val status = YoutubeDL.getInstance().updateYoutubeDL(context.applicationContext)
            Result.success("Engine updated successfully ($status)")
        } catch (e: Exception) {
            Log.e(TAG, "yt-dlp update error: ${e.message}", e)
            Result.failure(e)
        }
    }

    /**
     * Extracts video and playlist metadata without downloading media.
     */
    suspend fun fetchMetadata(context: Context, url: String): Result<MediaMetadata> = withContext(Dispatchers.IO) {
        try {
            ensureInitialized(context)
            val request = YoutubeDLRequest(url).apply {
                addOption("--skip-download")
                addOption("--flat-playlist")
                addOption("--no-warnings")
                addOption("--no-update")

                val isYouTube = url.contains("youtube.com", ignoreCase = true) || url.contains("youtu.be", ignoreCase = true)
                if (isYouTube) {
                    // Use iOS and Web clients to bypass mobile 360p/640p caps and access full 1080p DASH streams
                    addOption("--extractor-args", "youtube:player_client=ios,web")
                }
            }

            val videoInfo: VideoInfo = YoutubeDL.getInstance().getInfo(request)
            val title = videoInfo.title ?: "Untitled Media"
            val channel = videoInfo.uploader ?: "Unknown Creator"
            val durationSecs = videoInfo.duration
            val durationFormatted = if (durationSecs > 0) {
                val mins = durationSecs / 60
                val secs = durationSecs % 60
                String.format(Locale.US, "%02d:%02d", mins, secs)
            } else null

            val isPlaylist = url.contains("playlist", ignoreCase = true) || url.contains("list=", ignoreCase = true)
            val playlistItems = emptyList<PlaylistItem>()

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

            // Estimate sizes matching desktop logic based on duration and standard bitrates
            val qualities = listOf(
                QualityOption("best", "Best Available", "Source Maximum", false, estimateSize(durationSecs, 3628)),
                QualityOption("1080p", "Full HD 1080p", "1080p", false, estimateSize(durationSecs, 2628)),
                QualityOption("720p", "HD 720p", "720p", false, estimateSize(durationSecs, 1528)),
                QualityOption("480p", "Standard 480p", "480p", false, estimateSize(durationSecs, 878)),
                QualityOption("audio_mp3", "Audio Only (MP3)", "MP3 192kbps", true, estimateSize(durationSecs, 192))
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
     * Executes the download with real-time progress callbacks, pause/resume support,
     * un-capped resolution, and full playlist batch download support.
     */
    suspend fun executeDownload(
        context: Context,
        url: String,
        qualityId: String,
        targetDir: File,
        isPlaylist: Boolean = false,
        onProgress: (progress: Float, etaInSeconds: Long, line: String) -> Unit
    ): Result<List<File>> = withContext(Dispatchers.IO) {
        try {
            ensureInitialized(context)
            val request = YoutubeDLRequest(url).apply {
                addOption("-c") // Support resume for paused downloads
                addOption("--no-mtime")
                addOption("--windows-filenames")
                addOption("--no-warnings")
                addOption("--no-update")

                val isYouTube = url.contains("youtube.com", ignoreCase = true) || url.contains("youtu.be", ignoreCase = true)
                if (isYouTube) {
                    // Use iOS and Web clients to bypass mobile 360p/640p caps and access full 1080p DASH streams
                    addOption("--extractor-args", "youtube:player_client=ios,web")
                }

                if (isPlaylist) {
                    addOption("--yes-playlist")
                    addOption("-o", "${targetDir.absolutePath}/%(playlist_title,playlist)s/%(playlist_index)02d - %(title).100B [%(id)s].%(ext)s")
                } else {
                    addOption("--no-playlist")
                    addOption("-o", "${targetDir.absolutePath}/%(title).100B [%(id)s].%(ext)s")
                }

                when (qualityId) {
                    "audio_mp3" -> {
                        addOption("-x")
                        addOption("--audio-format", "mp3")
                        addOption("--audio-quality", "192K")
                    }
                    "1080p" -> {
                        addOption("-f", "bestvideo*[height<=?1080]+bestaudio/best[height<=?1080]/bestvideo*+bestaudio/best")
                        addOption("--format-sort", "res:1080,fps,vcodec:h264:vp9:av01,ext:mp4:m4a")
                        addOption("--merge-output-format", "mp4")
                    }
                    "720p" -> {
                        addOption("-f", "bestvideo*[height<=?720]+bestaudio/best[height<=?720]/bestvideo*+bestaudio/best")
                        addOption("--format-sort", "res:720,fps,vcodec:h264:vp9:av01,ext:mp4:m4a")
                        addOption("--merge-output-format", "mp4")
                    }
                    "480p" -> {
                        addOption("-f", "bestvideo*[height<=?480]+bestaudio/best[height<=?480]/bestvideo*+bestaudio/best")
                        addOption("--format-sort", "res:480,fps,vcodec:h264:vp9:av01,ext:mp4:m4a")
                        addOption("--merge-output-format", "mp4")
                    }
                    else -> {
                        addOption("-f", "bestvideo*+bestaudio/best")
                        addOption("--format-sort", "res,fps,vcodec:h264:vp9:av01,ext:mp4:m4a")
                        addOption("--merge-output-format", "mp4")
                    }
                }
            }

            YoutubeDL.getInstance().execute(request) { progress, eta, line ->
                onProgress(progress, eta, line ?: "")
            }

            // Find all completed media files in targetDir (including nested playlist folders)
            val mediaExtensions = setOf("mp4", "mp3", "mkv", "m4a", "webm", "opus", "flac")
            val downloadedFiles = targetDir.walkTopDown()
                .filter { it.isFile && it.extension.lowercase() in mediaExtensions && !it.name.endsWith(".part") }
                .sortedByDescending { it.lastModified() }
                .toList()

            if (downloadedFiles.isEmpty()) {
                throw IllegalStateException("Download finished but target media file not found on disk.")
            }

            Result.success(downloadedFiles)
        } catch (e: Exception) {
            val rawMsg = e.message ?: "Unknown error"
            val cleanMsg = rawMsg.lines()
                .filterNot { it.contains("WARNING: Your yt-dlp version") || it.contains("Run \"yt-dlp --update\"") || it.contains("To suppress this warning") }
                .joinToString("\n")
                .trim()
            Log.e(TAG, "Download execution failed: $cleanMsg", e)
            Result.failure(Exception(if (cleanMsg.isNotBlank()) cleanMsg else rawMsg, e))
        }
    }
}
