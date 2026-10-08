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

    private fun estimateSize(durationSecs: Int, kbps: Int, count: Int = 1): String {
        val effectiveDur = if (durationSecs > 0) durationSecs.toLong() else 210L // Default average ~3.5 min
        val singleBytes = (kbps.toLong() * 1000L / 8L) * effectiveDur
        val totalBytes = singleBytes * count.toLong().coerceAtLeast(1L)
        return if (count > 1) {
            "~${formatSizeBytes(totalBytes)} (${count} videos)"
        } else {
            "~${formatSizeBytes(totalBytes)}"
        }
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
     * Supports single videos, YouTube playlists, and multi-link batches.
     */
    suspend fun fetchMetadata(context: Context, input: String): Result<MediaMetadata> = withContext(Dispatchers.IO) {
        try {
            ensureInitialized(context)

            // Parse lines in case user pasted multiple links
            val rawUrls = input.lines()
                .map { it.trim() }
                .filter { it.startsWith("http://") || it.startsWith("https://") }

            val targetUrl = rawUrls.firstOrNull() ?: input.trim()
            val isMultiBatch = rawUrls.size > 1
            val isUrlPlaylist = targetUrl.contains("playlist", ignoreCase = true) || targetUrl.contains("list=", ignoreCase = true)
            val isPlaylistUrl = isUrlPlaylist || isMultiBatch

            val isYouTube = targetUrl.contains("youtube.com", ignoreCase = true) || targetUrl.contains("youtu.be", ignoreCase = true)
            val request = YoutubeDLRequest(targetUrl).apply {
                addOption("--skip-download")
                addOption("--no-warnings")
                addOption("--no-update")

                // Only use flat-playlist for playlist URLs so single videos get full metadata and duration
                if (isUrlPlaylist) {
                    addOption("--flat-playlist")
                }

                // player_client=ios is only for individual video streams, breaks playlist tab endpoints
                if (isYouTube && !isPlaylistUrl) {
                    addOption("--extractor-args", "youtube:player_client=ios,web")
                }
            }

            val videoInfo: VideoInfo? = try {
                YoutubeDL.getInstance().getInfo(request)
            } catch (e: Exception) {
                Log.w(TAG, "getInfo failed: ${e.message}")
                if (isPlaylistUrl) null else throw e
            }

            val rawTitle = videoInfo?.title ?: if (isMultiBatch) "Batch (${rawUrls.size} items)" else "YouTube Playlist"
            val channel = videoInfo?.uploader ?: if (isMultiBatch) "Batch Downloader" else "Playlist Collection"
            val durationSecs = videoInfo?.duration ?: 0

            val durationFormatted = if (durationSecs > 0) {
                val mins = durationSecs / 60
                val secs = durationSecs % 60
                String.format(Locale.US, "%02d:%02d", mins, secs)
            } else null

            // Extract entries if available from playlist info
            val entries: List<VideoInfo>? = try {
                videoInfo?.entries
            } catch (e: Exception) {
                null
            }

            val playlistItems = when {
                isMultiBatch -> {
                    rawUrls.mapIndexed { idx, u ->
                        PlaylistItem(
                            id = "$idx",
                            title = "Video ${idx + 1}",
                            url = u
                        )
                    }
                }
                entries != null && entries.isNotEmpty() -> {
                    entries.mapIndexed { idx, item ->
                        val itemDuration = item.duration
                        val itemDurFormatted = if (itemDuration > 0) {
                            val mins = itemDuration / 60
                            val secs = itemDuration % 60
                            String.format(Locale.US, "%02d:%02d", mins, secs)
                        } else null
                        PlaylistItem(
                            id = item.id ?: "${idx + 1}",
                            title = item.title ?: "Video ${idx + 1}",
                            url = item.webpageUrl ?: item.url ?: "https://www.youtube.com/watch?v=${item.id ?: ""}",
                            durationFormatted = itemDurFormatted,
                            thumbnail = item.thumbnail
                        )
                    }
                }
                else -> emptyList()
            }

            val totalItemCount = if (playlistItems.isNotEmpty()) playlistItems.size else if (isPlaylistUrl) 10 else 1

            val platform = when {
                targetUrl.contains("youtube.com", true) || targetUrl.contains("youtu.be", true) -> "YouTube"
                targetUrl.contains("instagram.com", true) -> "Instagram"
                targetUrl.contains("tiktok.com", true) -> "TikTok"
                targetUrl.contains("twitter.com", true) || targetUrl.contains("x.com", true) -> "X (Twitter)"
                targetUrl.contains("bilibili.com", true) -> "Bilibili"
                targetUrl.contains("facebook.com", true) -> "Facebook"
                targetUrl.contains("reddit.com", true) -> "Reddit"
                else -> "Universal"
            }

            // Estimate sizes matching desktop logic: Always guarantee realistic non-null sizes
            val qualities = listOf(
                QualityOption("best", "Best Available", "Source Maximum", false, estimateSize(durationSecs, 3628, totalItemCount)),
                QualityOption("1080p", "Full HD 1080p", "1080p", false, estimateSize(durationSecs, 2628, totalItemCount)),
                QualityOption("720p", "HD 720p", "720p", false, estimateSize(durationSecs, 1528, totalItemCount)),
                QualityOption("480p", "Standard 480p", "480p", false, estimateSize(durationSecs, 878, totalItemCount)),
                QualityOption("audio_mp3", "Audio Only (MP3)", "MP3 192kbps", true, estimateSize(durationSecs, 192, totalItemCount))
            )

            Result.success(
                MediaMetadata(
                    url = input.trim(),
                    title = rawTitle,
                    channel = channel,
                    durationFormatted = durationFormatted,
                    thumbnail = videoInfo?.thumbnail,
                    platform = platform,
                    isPlaylist = isPlaylistUrl,
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
     * un-capped resolution, and full playlist & batch download support.
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

            // Extract all URLs if user provided multiple links (batch)
            val urls = url.lines()
                .map { it.trim() }
                .filter { it.startsWith("http://") || it.startsWith("https://") }
                .ifEmpty { listOf(url.trim()) }

            val configureRequest: (YoutubeDLRequest, String, Boolean, Int) -> Unit = { req, targetUrl, isPl, itemIndex ->
                req.addOption("-c") // Support resume for paused downloads
                req.addOption("--no-mtime")
                req.addOption("--windows-filenames")
                req.addOption("--no-warnings")
                req.addOption("--no-update")

                val isYouTube = targetUrl.contains("youtube.com", ignoreCase = true) || targetUrl.contains("youtu.be", ignoreCase = true)
                if (isYouTube && !isPl) {
                    req.addOption("--extractor-args", "youtube:player_client=ios,web")
                }

                if (isPl) {
                    req.addOption("--yes-playlist")
                    req.addOption("-i") // Continue past broken/private videos so entire playlist finishes
                    req.addOption("--no-abort-on-error")
                    req.addOption("-o", "${targetDir.absolutePath}/%(autonumber)03d - %(title).100B [%(id)s].%(ext)s")
                } else if (urls.size > 1) {
                    val prefix = String.format(Locale.US, "%03d", itemIndex + 1)
                    req.addOption("--no-playlist")
                    req.addOption("-o", "${targetDir.absolutePath}/$prefix - %(title).100B [%(id)s].%(ext)s")
                } else {
                    req.addOption("--no-playlist")
                    req.addOption("-o", "${targetDir.absolutePath}/%(title).100B [%(id)s].%(ext)s")
                }

                when (qualityId) {
                    "audio_mp3" -> {
                        req.addOption("-x")
                        req.addOption("--audio-format", "mp3")
                        req.addOption("--audio-quality", "192K")
                    }
                    "1080p" -> {
                        req.addOption("-f", "bestvideo*[height<=?1080]+bestaudio/best[height<=?1080]/bestvideo*+bestaudio/best")
                        req.addOption("--format-sort", "res:1080,fps,vcodec:h264:vp9:av01,ext:mp4:m4a")
                        req.addOption("--merge-output-format", "mp4")
                    }
                    "720p" -> {
                        req.addOption("-f", "bestvideo*[height<=?720]+bestaudio/best[height<=?720]/bestvideo*+bestaudio/best")
                        req.addOption("--format-sort", "res:720,fps,vcodec:h264:vp9:av01,ext:mp4:m4a")
                        req.addOption("--merge-output-format", "mp4")
                    }
                    "480p" -> {
                        req.addOption("-f", "bestvideo*[height<=?480]+bestaudio/best[height<=?480]/bestvideo*+bestaudio/best")
                        req.addOption("--format-sort", "res:480,fps,vcodec:h264:vp9:av01,ext:mp4:m4a")
                        req.addOption("--merge-output-format", "mp4")
                    }
                    else -> {
                        req.addOption("-f", "bestvideo*+bestaudio/best")
                        req.addOption("--format-sort", "res,fps,vcodec:h264:vp9:av01,ext:mp4:m4a")
                        req.addOption("--merge-output-format", "mp4")
                    }
                }
            }

            if (urls.size > 1) {
                // Multi-link batch downloading
                for ((idx, singleUrl) in urls.withIndex()) {
                    try {
                        val req = YoutubeDLRequest(singleUrl)
                        configureRequest(req, singleUrl, false, idx)
                        YoutubeDL.getInstance().execute(req) { progress, eta, line ->
                            val overallProgress = ((idx.toFloat() + (progress / 100f)) / urls.size.toFloat()) * 100f
                            val batchLine = "Downloading video ${idx + 1} of ${urls.size} • ${line ?: ""}"
                            onProgress(overallProgress, eta, batchLine)
                        }
                    } catch (itemErr: Exception) {
                        Log.w(TAG, "Batch item ${idx + 1} failed: ${itemErr.message}", itemErr)
                    }
                }
            } else {
                // Single video or YouTube playlist
                val singleUrl = urls.first()
                val isTargetPlaylist = isPlaylist || singleUrl.contains("playlist", ignoreCase = true) || singleUrl.contains("list=", ignoreCase = true)
                val req = YoutubeDLRequest(singleUrl)
                configureRequest(req, singleUrl, isTargetPlaylist, 0)
                try {
                    YoutubeDL.getInstance().execute(req) { progress, eta, line ->
                        onProgress(progress, eta, line ?: "")
                    }
                } catch (execErr: Exception) {
                    Log.w(TAG, "Download execution notice: ${execErr.message}")
                }
            }

            // Find all completed media files in targetDir
            val mediaExtensions = setOf("mp4", "mp3", "mkv", "m4a", "webm", "opus", "flac")
            val downloadedFiles = targetDir.walkTopDown()
                .filter { it.isFile && it.extension.lowercase() in mediaExtensions && !it.name.endsWith(".part") }
                .sortedBy { it.name }
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
