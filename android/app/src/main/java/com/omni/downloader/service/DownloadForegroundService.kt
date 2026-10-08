package com.omni.downloader.service

import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.IBinder
import android.os.PowerManager
import android.util.Log
import androidx.core.app.NotificationCompat
import com.omni.downloader.MainActivity
import com.omni.downloader.OmniApplication
import com.omni.downloader.data.DownloadTracker
import com.omni.downloader.data.models.DownloadTaskProgress
import com.omni.downloader.data.models.TaskStatus
import com.omni.downloader.engine.StorageHelper
import com.omni.downloader.engine.YoutubeDLEngine
import kotlinx.coroutines.*
import java.util.UUID

class DownloadForegroundService : Service() {

    private val serviceScope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private var downloadJob: Job? = null
    private var wakeLock: PowerManager.WakeLock? = null

    private var activeTaskId: String = UUID.randomUUID().toString()
    private var activeUrl: String = ""
    private var activeQuality: String = "best"
    private var activeTitle: String = "Media Download"
    private var activeIsAudio: Boolean = false
    private var activeIsPlaylist: Boolean = false
    private var isPaused: Boolean = false

    private var playlistCompleted: Int = 0
    private var playlistTotal: Int = 1

    companion object {
        const val NOTIFICATION_ID = 1001
        const val ACTION_START = "ACTION_START_DOWNLOAD"
        const val ACTION_PAUSE = "ACTION_PAUSE_DOWNLOAD"
        const val ACTION_RESUME = "ACTION_RESUME_DOWNLOAD"
        const val ACTION_CANCEL = "ACTION_CANCEL_DOWNLOAD"

        const val EXTRA_URL = "EXTRA_URL"
        const val EXTRA_QUALITY = "EXTRA_QUALITY"
        const val EXTRA_TITLE = "EXTRA_TITLE"
        const val EXTRA_IS_AUDIO = "EXTRA_IS_AUDIO"
        const val EXTRA_IS_PLAYLIST = "EXTRA_IS_PLAYLIST"

        private const val TAG = "DownloadService"

        fun startDownload(
            context: Context,
            url: String,
            quality: String,
            title: String,
            isAudio: Boolean,
            isPlaylist: Boolean = false
        ) {
            val intent = Intent(context, DownloadForegroundService::class.java).apply {
                action = ACTION_START
                putExtra(EXTRA_URL, url)
                putExtra(EXTRA_QUALITY, quality)
                putExtra(EXTRA_TITLE, title)
                putExtra(EXTRA_IS_AUDIO, isAudio)
                putExtra(EXTRA_IS_PLAYLIST, isPlaylist)
            }
            context.startService(intent)
        }

        fun pauseDownload(context: Context) {
            val intent = Intent(context, DownloadForegroundService::class.java).apply {
                action = ACTION_PAUSE
            }
            context.startService(intent)
        }

        fun resumeDownload(context: Context) {
            val intent = Intent(context, DownloadForegroundService::class.java).apply {
                action = ACTION_RESUME
            }
            context.startService(intent)
        }

        fun cancelDownload(context: Context) {
            val intent = Intent(context, DownloadForegroundService::class.java).apply {
                action = ACTION_CANCEL
            }
            context.startService(intent)
        }
    }

    override fun onCreate() {
        super.onCreate()
        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "OmniDownloader::DownloadWakeLock").apply {
            acquire(60 * 60 * 1000L) // Max 60 minutes for large playlists
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> {
                activeUrl = intent.getStringExtra(EXTRA_URL) ?: return START_NOT_STICKY
                activeQuality = intent.getStringExtra(EXTRA_QUALITY) ?: "best"
                activeTitle = intent.getStringExtra(EXTRA_TITLE) ?: "Media Download"
                activeIsAudio = intent.getBooleanExtra(EXTRA_IS_AUDIO, false)
                activeIsPlaylist = intent.getBooleanExtra(EXTRA_IS_PLAYLIST, false)

                activeTaskId = UUID.randomUUID().toString()
                isPaused = false
                playlistCompleted = 0
                playlistTotal = 1

                DownloadTracker.updateProgress(
                    DownloadTaskProgress(
                        taskId = activeTaskId,
                        status = TaskStatus.DOWNLOADING,
                        progressPercent = 0f,
                        currentTitle = activeTitle,
                        totalItems = if (activeIsPlaylist) 0 else 1
                    )
                )

                startForeground(NOTIFICATION_ID, buildProgressNotification(activeTitle, 0f, "Starting download..."))
                runDownload()
            }

            ACTION_PAUSE -> {
                isPaused = true
                downloadJob?.cancel()
                val current = DownloadTracker.activeTask.value
                if (current != null) {
                    DownloadTracker.updateProgress(
                        current.copy(
                            status = TaskStatus.PAUSED,
                            speedFormatted = "--"
                        )
                    )
                }
                val notificationManager = getSystemService(NotificationManager::class.java)
                notificationManager?.notify(NOTIFICATION_ID, buildPausedNotification(activeTitle))
            }

            ACTION_RESUME -> {
                if (isPaused && activeUrl.isNotBlank()) {
                    isPaused = false
                    val current = DownloadTracker.activeTask.value
                    if (current != null) {
                        DownloadTracker.updateProgress(
                            current.copy(status = TaskStatus.DOWNLOADING)
                        )
                    }
                    val notificationManager = getSystemService(NotificationManager::class.java)
                    notificationManager?.notify(NOTIFICATION_ID, buildProgressNotification(activeTitle, 0f, "Resuming download..."))
                    runDownload()
                }
            }

            ACTION_CANCEL -> {
                isPaused = false
                downloadJob?.cancel()
                DownloadTracker.updateProgress(
                    DownloadTaskProgress(
                        taskId = activeTaskId,
                        status = TaskStatus.CANCELLED,
                        currentTitle = activeTitle,
                        errorMessage = "Cancelled by user"
                    )
                )
                val notificationManager = getSystemService(NotificationManager::class.java)
                notificationManager?.cancel(NOTIFICATION_ID)
                stopSelf()
            }
        }
        return START_NOT_STICKY
    }

    private fun runDownload() {
        downloadJob = serviceScope.launch {
            val tempDir = StorageHelper.getTempDownloadDir(this@DownloadForegroundService)
            val result = YoutubeDLEngine.executeDownload(
                context = this@DownloadForegroundService,
                url = activeUrl,
                qualityId = activeQuality,
                targetDir = tempDir,
                isPlaylist = activeIsPlaylist
            ) { progress, eta, line ->
                val etaText = if (eta > 0) "${eta}s remaining" else ""
                val speed = extractSpeed(line)

                // Detect playlist progress lines: e.g. "Downloading video 3 of 12"
                val playlistMatch = Regex("""Downloading (?:video|item)\s+(\d+)\s+of\s+(\d+)""").find(line)
                if (playlistMatch != null) {
                    playlistCompleted = playlistMatch.groupValues[1].toIntOrNull() ?: playlistCompleted
                    playlistTotal = playlistMatch.groupValues[2].toIntOrNull() ?: playlistTotal
                }

                val statusText = if (playlistTotal > 1) {
                    "Item $playlistCompleted of $playlistTotal • ${progress.toInt()}% • $speed"
                } else {
                    "${progress.toInt()}% • $speed"
                }

                updateNotification(activeTitle, progress, statusText)
                DownloadTracker.updateProgress(
                    DownloadTaskProgress(
                        taskId = activeTaskId,
                        status = TaskStatus.DOWNLOADING,
                        progressPercent = progress,
                        etaFormatted = etaText,
                        speedFormatted = speed,
                        currentTitle = activeTitle,
                        completedItems = playlistCompleted,
                        totalItems = playlistTotal
                    )
                )
            }

            result.onSuccess { completedFiles ->
                var lastSavedUri: String? = null
                var savedCount = 0

                for (file in completedFiles) {
                    val mediaUri = StorageHelper.saveToPublicMedia(
                        context = this@DownloadForegroundService,
                        sourceFile = file,
                        title = file.nameWithoutExtension,
                        isAudio = activeIsAudio
                    )
                    if (mediaUri != null) {
                        lastSavedUri = mediaUri.toString()
                        savedCount++
                    }
                    file.delete()
                }

                DownloadTracker.updateProgress(
                    DownloadTaskProgress(
                        taskId = activeTaskId,
                        status = TaskStatus.COMPLETED,
                        progressPercent = 100f,
                        currentTitle = activeTitle,
                        completedItems = savedCount,
                        totalItems = savedCount.coerceAtLeast(1),
                        savedFilePath = lastSavedUri
                    )
                )
                showCompleteNotification(activeTitle, savedCount)
                stopSelf()
            }.onFailure { error ->
                if (!isPaused && isActive) {
                    Log.e(TAG, "Download failed: ${error.message}", error)
                    DownloadTracker.updateProgress(
                        DownloadTaskProgress(
                            taskId = activeTaskId,
                            status = TaskStatus.FAILED,
                            currentTitle = activeTitle,
                            errorMessage = error.message ?: "Download failed"
                        )
                    )
                    showFailedNotification(activeTitle, error.message ?: "Download encountered an error")
                    stopSelf()
                }
            }
        }
    }

    private fun extractSpeed(line: String): String {
        val match = Regex("""at\s+([0-9.]+\s*[kKmMgG]i?B/s)""").find(line)
        return match?.groupValues?.get(1) ?: "--"
    }

    private fun buildProgressNotification(title: String, progress: Float, statusText: String): android.app.Notification {
        val pauseIntent = Intent(this, DownloadForegroundService::class.java).apply {
            action = ACTION_PAUSE
        }
        val pausePendingIntent = PendingIntent.getService(this, 2, pauseIntent, PendingIntent.FLAG_IMMUTABLE)

        val cancelIntent = Intent(this, DownloadForegroundService::class.java).apply {
            action = ACTION_CANCEL
        }
        val cancelPendingIntent = PendingIntent.getService(this, 1, cancelIntent, PendingIntent.FLAG_IMMUTABLE)

        return NotificationCompat.Builder(this, OmniApplication.CHANNEL_ID)
            .setContentTitle("Downloading: $title")
            .setContentText(statusText)
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setProgress(100, progress.toInt().coerceIn(0, 100), false)
            .setOngoing(true)
            .setContentIntent(getLaunchIntent())
            .addAction(android.R.drawable.ic_media_pause, "Pause", pausePendingIntent)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Cancel", cancelPendingIntent)
            .build()
    }

    private fun buildPausedNotification(title: String): android.app.Notification {
        val resumeIntent = Intent(this, DownloadForegroundService::class.java).apply {
            action = ACTION_RESUME
        }
        val resumePendingIntent = PendingIntent.getService(this, 3, resumeIntent, PendingIntent.FLAG_IMMUTABLE)

        val cancelIntent = Intent(this, DownloadForegroundService::class.java).apply {
            action = ACTION_CANCEL
        }
        val cancelPendingIntent = PendingIntent.getService(this, 1, cancelIntent, PendingIntent.FLAG_IMMUTABLE)

        return NotificationCompat.Builder(this, OmniApplication.CHANNEL_ID)
            .setContentTitle("Paused: $title")
            .setContentText("Download paused. Tap Resume to continue.")
            .setSmallIcon(android.R.drawable.ic_media_pause)
            .setOngoing(true)
            .setContentIntent(getLaunchIntent())
            .addAction(android.R.drawable.ic_media_play, "Resume", resumePendingIntent)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Cancel", cancelPendingIntent)
            .build()
    }

    private fun updateNotification(title: String, progress: Float, statusText: String) {
        val notificationManager = getSystemService(NotificationManager::class.java)
        notificationManager?.notify(
            NOTIFICATION_ID,
            buildProgressNotification(title, progress, statusText)
        )
    }

    private fun showCompleteNotification(title: String, savedCount: Int) {
        val notificationManager = getSystemService(NotificationManager::class.java)
        val text = if (savedCount > 1) {
            "Playlist downloaded: $savedCount videos saved to Media Library."
        } else {
            "$title saved to your media library."
        }
        val notif = NotificationCompat.Builder(this, OmniApplication.CHANNEL_ID)
            .setContentTitle("Download Complete")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.stat_sys_download_done)
            .setAutoCancel(true)
            .setContentIntent(getLaunchIntent())
            .build()
        notificationManager?.notify(NOTIFICATION_ID + 1, notif)
    }

    private fun showFailedNotification(title: String, error: String) {
        val notificationManager = getSystemService(NotificationManager::class.java)
        val notif = NotificationCompat.Builder(this, OmniApplication.CHANNEL_ID)
            .setContentTitle("Download Failed")
            .setContentText("$title: $error")
            .setSmallIcon(android.R.drawable.stat_notify_error)
            .setAutoCancel(true)
            .build()
        notificationManager?.notify(NOTIFICATION_ID + 2, notif)
    }

    private fun getLaunchIntent(): PendingIntent {
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP
        }
        return PendingIntent.getActivity(this, 0, intent, PendingIntent.FLAG_IMMUTABLE)
    }

    override fun onDestroy() {
        super.onDestroy()
        downloadJob?.cancel()
        serviceScope.cancel()
        try {
            if (wakeLock?.isHeld == true) {
                wakeLock?.release()
            }
        } catch (e: Exception) {
            Log.w(TAG, "Error releasing wakeLock: ${e.message}")
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
