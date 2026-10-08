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
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale

object YoutubeDLEngine {
    private const val TAG = "YoutubeDLEngine"
    private const val BROWSER_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

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
     * Preprocesses and resolves redirect URLs for shortlinks (b23.tv, reddit /s/ shares)
     * and strips tracking tokens from Instagram reels.
     */
    private suspend fun preprocessUrl(rawUrl: String): String = withContext(Dispatchers.IO) {
        var url = rawUrl.trim()

        // Strip Instagram query tracking tokens (?stkn=..., ?igsh=...)
        if (url.contains("instagram.com", ignoreCase = true)) {
            val qIdx = url.indexOf('?')
            if (qIdx != -1) {
                url = url.substring(0, qIdx)
            }
        }

        // Strip Reddit query tracking if not /s/ share
        if (url.contains("reddit.com", ignoreCase = true) && !url.contains("/s/")) {
            val qIdx = url.indexOf('?')
            if (qIdx != -1) {
                url = url.substring(0, qIdx)
            }
        }

        // Follow HTTP redirects for shortlinks to get canonical endpoints
        val needsResolution = url.contains("b23.tv", ignoreCase = true) ||
                (url.contains("reddit.com", ignoreCase = true) && url.contains("/s/")) ||
                url.contains("t.co", ignoreCase = true)

        if (needsResolution) {
            try {
                var current = url
                var redirects = 0
                while (redirects < 5) {
                    val conn = (URL(current).openConnection() as HttpURLConnection).apply {
                        instanceFollowRedirects = false
                        connectTimeout = 6000
                        readTimeout = 6000
                        setRequestProperty("User-Agent", BROWSER_USER_AGENT)
                        setRequestProperty("Accept-Language", "en-US,en;q=0.9")
                    }
                    val code = conn.responseCode
                    if (code in 300..399) {
                        val loc = conn.getHeaderField("Location")
                        conn.disconnect()
                        if (loc != null) {
                            current = if (loc.startsWith("/")) {
                                val base = URL(current)
                                "${base.protocol}://${base.host}$loc"
                            } else {
                                loc
                            }
                            redirects++
                            continue
                        }
                    }
                    conn.disconnect()
                    break
                }
                url = current
            } catch (e: Exception) {
                Log.w(TAG, "Shortlink redirect resolution notice: ${e.message}")
            }
        }

        url
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

            val rawTarget = rawUrls.firstOrNull() ?: input.trim()
            val targetUrl = preprocessUrl(rawTarget)
            val isMultiBatch = rawUrls.size > 1
            val isUrlPlaylist = targetUrl.contains("playlist", ignoreCase = true) || targetUrl.contains("list=", ignoreCase = true)
            val isPlaylistUrl = isUrlPlaylist || isMultiBatch

            val applyHeaders: (YoutubeDLRequest, String) -> Unit = { req, url ->
                req.addOption("--skip-download")
                req.addOption("--no-warnings")
                req.addOption("--no-update")
                req.addOption("--no-check-certificates")
                req.addOption("--user-agent", BROWSER_USER_AGENT)
                req.addOption("--add-header", "Accept-Language:en-US,en;q=0.9")

                if (url.contains("bilibili.com", ignoreCase = true) || url.contains("b23.tv", ignoreCase = true)) {
                    req.addOption("--add-header", "Referer:https://www.bilibili.com")
                    req.addOption("--add-header", "Origin:https://www.bilibili.com")
                }

                if (url.contains("instagram.com", ignoreCase = true)) {
                    req.addOption("--add-header", "Referer:https://www.instagram.com/")
                }

                if (url.contains("reddit.com", ignoreCase = true)) {
                    req.addOption("--add-header", "Referer:https://www.reddit.com/")
                }

                if (isUrlPlaylist) {
                    req.addOption("--flat-playlist")
                }
            }

            val request = YoutubeDLRequest(targetUrl).apply {
                applyHeaders(this, targetUrl)
            }

            var videoInfo: VideoInfo? = null
            try {
                videoInfo = YoutubeDL.getInstance().getInfo(request)
            } catch (e: Exception) {
                val isYouTube = targetUrl.contains("youtube.com", ignoreCase = true) || targetUrl.contains("youtu.be", ignoreCase = true)
                if (isYouTube && !isPlaylistUrl) {
                    // Fallback to android client extraction if standard extraction failed
                    try {
                        val fbRequest = YoutubeDLRequest(targetUrl).apply {
                            applyHeaders(this, targetUrl)
                            addOption("--extractor-args", "youtube:player_client=android,web")
                        }
                        videoInfo = YoutubeDL.getInstance().getInfo(fbRequest)
                    } catch (fbErr: Exception) {
                        Log.w(TAG, "Android fallback client also failed: ${fbErr.message}")
                        if (!isPlaylistUrl) throw e
                    }
                } else if (!isPlaylistUrl) {
                    throw e
                }
            }

            val rawTitle = videoInfo?.title ?: if (isMultiBatch) "Batch (${rawUrls.size} items)" else "YouTube Playlist"
            val channel = videoInfo?.uploader ?: if (isMultiBatch) "Batch Downloader" else "Playlist Collection"
            val durationSecs = videoInfo?.duration ?: 0

            val durationFormatted = if (durationSecs > 0) {
                val mins = durationSecs / 60
                val secs = durationSecs % 60
                String.format(Locale.US, "%02d:%02d", mins, secs)
            } else null

            val playlistItems = if (isMultiBatch) {
                rawUrls.mapIndexed { idx, u ->
                    PlaylistItem(
                        id = "$idx",
                        title = "Video ${idx + 1}",
                        url = u,
                        isSelected = true
                    )
                }
            } else if (isUrlPlaylist) {
                try {
                    val plRequest = YoutubeDLRequest(targetUrl).apply {
                        addOption("--flat-playlist")
                        addOption("--skip-download")
                        addOption("--no-warnings")
                        addOption("--no-check-certificates")
                        addOption("--user-agent", BROWSER_USER_AGENT)
                        addOption("--print", "%(id)s\t%(title)s")
                    }
                    val plResponse = YoutubeDL.getInstance().execute(plRequest)
                    val rawLines = plResponse.out?.lines()?.map { it.trim() }?.filter { it.isNotEmpty() } ?: emptyList()
                    rawLines.mapIndexed { idx, line ->
                        val tabIdx = line.indexOf('\t')
                        val id = if (tabIdx != -1) line.substring(0, tabIdx).trim() else line
                        val title = if (tabIdx != -1) line.substring(tabIdx + 1).trim() else "Video ${idx + 1}"
                        val videoUrl = if (targetUrl.contains("youtube.com") || targetUrl.contains("youtu.be")) {
                            "https://www.youtube.com/watch?v=$id"
                        } else {
                            id
                        }
                        PlaylistItem(
                            id = id,
                            title = title.ifBlank { "Video ${idx + 1}" },
                            url = videoUrl,
                            isSelected = true
                        )
                    }
                } catch (plErr: Exception) {
                    Log.w(TAG, "Fast playlist entries extraction notice: ${plErr.message}")
                    emptyList()
                }
            } else {
                emptyList()
            }

            val totalItemCount = if (playlistItems.isNotEmpty()) playlistItems.size else if (isPlaylistUrl) 10 else 1

            val platform = when {
                targetUrl.contains("youtube.com", true) || targetUrl.contains("youtu.be", true) -> "YouTube"
                targetUrl.contains("instagram.com", true) -> "Instagram"
                targetUrl.contains("tiktok.com", true) -> "TikTok"
                targetUrl.contains("twitter.com", true) || targetUrl.contains("x.com", true) -> "X (Twitter)"
                targetUrl.contains("bilibili.com", true) || targetUrl.contains("b23.tv", true) -> "Bilibili"
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
                    url = targetUrl,
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
                req.addOption("--no-check-certificates")
                req.addOption("--user-agent", BROWSER_USER_AGENT)
                req.addOption("--add-header", "Accept-Language:en-US,en;q=0.9")

                if (targetUrl.contains("bilibili.com", ignoreCase = true) || targetUrl.contains("b23.tv", ignoreCase = true)) {
                    req.addOption("--add-header", "Referer:https://www.bilibili.com")
                    req.addOption("--add-header", "Origin:https://www.bilibili.com")
                }

                if (targetUrl.contains("instagram.com", ignoreCase = true)) {
                    req.addOption("--add-header", "Referer:https://www.instagram.com/")
                }

                if (targetUrl.contains("reddit.com", ignoreCase = true)) {
                    req.addOption("--add-header", "Referer:https://www.reddit.com/")
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
                        req.addOption("-f", "bv*[height<=?1080]+ba/b[height<=?1080]/bv*+ba/best")
                        req.addOption("--format-sort", "res:1080,fps,vcodec:h264:vp9:av01,ext:mp4:m4a")
                        req.addOption("--merge-output-format", "mp4")
                    }
                    "720p" -> {
                        req.addOption("-f", "bv*[height<=?720]+ba/b[height<=?720]/bv*+ba/best")
                        req.addOption("--format-sort", "res:720,fps,vcodec:h264:vp9:av01,ext:mp4:m4a")
                        req.addOption("--merge-output-format", "mp4")
                    }
                    "480p" -> {
                        req.addOption("-f", "bv*[height<=?480]+ba/b[height<=?480]/bv*+ba/best")
                        req.addOption("--format-sort", "res:480,fps,vcodec:h264:vp9:av01,ext:mp4:m4a")
                        req.addOption("--merge-output-format", "mp4")
                    }
                    else -> {
                        req.addOption("-f", "bv*+ba/b/best")
                        req.addOption("--format-sort", "res,fps,vcodec:h264:vp9:av01,ext:mp4:m4a")
                        req.addOption("--merge-output-format", "mp4")
                    }
                }
            }

            var downloadError: Exception? = null

            if (urls.size > 1) {
                // Multi-link batch downloading
                for ((idx, rawSingleUrl) in urls.withIndex()) {
                    try {
                        val singleUrl = preprocessUrl(rawSingleUrl)
                        val req = YoutubeDLRequest(singleUrl)
                        configureRequest(req, singleUrl, false, idx)
                        YoutubeDL.getInstance().execute(req) { progress, eta, line ->
                            val overallProgress = ((idx.toFloat() + (progress / 100f)) / urls.size.toFloat()) * 100f
                            val batchLine = "Downloading video ${idx + 1} of ${urls.size} • ${line ?: ""}"
                            onProgress(overallProgress, eta, batchLine)
                        }
                    } catch (itemErr: Exception) {
                        Log.w(TAG, "Batch item ${idx + 1} failed: ${itemErr.message}", itemErr)
                        downloadError = itemErr
                    }
                }
            } else {
                // Single video or YouTube playlist
                val rawSingleUrl = urls.first()
                val singleUrl = preprocessUrl(rawSingleUrl)
                val isTargetPlaylist = isPlaylist || singleUrl.contains("playlist", ignoreCase = true) || singleUrl.contains("list=", ignoreCase = true)
                val req = YoutubeDLRequest(singleUrl)
                configureRequest(req, singleUrl, isTargetPlaylist, 0)
                try {
                    YoutubeDL.getInstance().execute(req) { progress, eta, line ->
                        onProgress(progress, eta, line ?: "")
                    }
                } catch (execErr: Exception) {
                    Log.w(TAG, "Download execution error: ${execErr.message}", execErr)
                    downloadError = execErr
                }
            }

            // Find all completed media files in targetDir
            val mediaExtensions = setOf("mp4", "mp3", "mkv", "m4a", "webm", "opus", "flac")
            val downloadedFiles = targetDir.walkTopDown()
                .filter { it.isFile && it.extension.lowercase() in mediaExtensions && !it.name.endsWith(".part") }
                .sortedBy { it.name }
                .toList()

            if (downloadedFiles.isEmpty()) {
                if (downloadError != null) {
                    throw downloadError
                } else {
                    throw IllegalStateException("Download finished but target media file not found on disk.")
                }
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
