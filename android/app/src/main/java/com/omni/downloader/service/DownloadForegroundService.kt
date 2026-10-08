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
    private var currentTaskId: String = UUID.randomUUID().toString()
    private var currentTitle: String = "Media Download"

    companion object {
        const val NOTIFICATION_ID = 1001
        const val ACTION_START = "ACTION_START_DOWNLOAD"
        const val ACTION_CANCEL = "ACTION_CANCEL_DOWNLOAD"

        const val EXTRA_URL = "EXTRA_URL"
        const val EXTRA_QUALITY = "EXTRA_QUALITY"
        const val EXTRA_TITLE = "EXTRA_TITLE"
        const val EXTRA_IS_AUDIO = "EXTRA_IS_AUDIO"

        private const val TAG = "DownloadService"

        fun startDownload(context: Context, url: String, quality: String, title: String, isAudio: Boolean) {
            val intent = Intent(context, DownloadForegroundService::class.java).apply {
                action = ACTION_START
                putExtra(EXTRA_URL, url)
                putExtra(EXTRA_QUALITY, quality)
                putExtra(EXTRA_TITLE, title)
                putExtra(EXTRA_IS_AUDIO, isAudio)
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
            acquire(30 * 60 * 1000L) // Max 30 minutes
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val action = intent?.action
        if (action == ACTION_START) {
            val url = intent.getStringExtra(EXTRA_URL) ?: return START_NOT_STICKY
            val quality = intent.getStringExtra(EXTRA_QUALITY) ?: "best"
            val title = intent.getStringExtra(EXTRA_TITLE) ?: "Media Download"
            val isAudio = intent.getBooleanExtra(EXTRA_IS_AUDIO, false)

            currentTaskId = UUID.randomUUID().toString()
            currentTitle = title

            DownloadTracker.updateProgress(
                DownloadTaskProgress(
                    taskId = currentTaskId,
                    status = TaskStatus.DOWNLOADING,
                    progressPercent = 0f,
                    currentTitle = title
                )
            )

            startForeground(NOTIFICATION_ID, buildProgressNotification(title, 0f, "Starting download..."))
            runDownload(url, quality, title, isAudio)
        } else if (action == ACTION_CANCEL) {
            downloadJob?.cancel()
            DownloadTracker.updateProgress(
                DownloadTaskProgress(
                    taskId = currentTaskId,
                    status = TaskStatus.CANCELLED,
                    currentTitle = currentTitle,
                    errorMessage = "Cancelled by user"
                )
            )
            val notificationManager = getSystemService(NotificationManager::class.java)
            notificationManager?.cancel(NOTIFICATION_ID)
            stopSelf()
        }
        return START_NOT_STICKY
    }

    private fun runDownload(url: String, quality: String, title: String, isAudio: Boolean) {
        downloadJob = serviceScope.launch {
            val tempDir = StorageHelper.getTempDownloadDir(this@DownloadForegroundService)
            val result = YoutubeDLEngine.executeDownload(
                context = this@DownloadForegroundService,
                url = url,
                qualityId = quality,
                targetDir = tempDir
            ) { progress, eta, line ->
                val etaText = if (eta > 0) "${eta}s remaining" else ""
                val speed = extractSpeed(line)
                updateNotification(title, progress, etaText)
                DownloadTracker.updateProgress(
                    DownloadTaskProgress(
                        taskId = currentTaskId,
                        status = TaskStatus.DOWNLOADING,
                        progressPercent = progress,
                        etaFormatted = etaText,
                        speedFormatted = speed,
                        currentTitle = title
                    )
                )
            }

            result.onSuccess { tempFile ->
                val mediaUri = StorageHelper.saveToPublicMedia(
                    context = this@DownloadForegroundService,
                    sourceFile = tempFile,
                    title = title,
                    isAudio = isAudio
                )
                tempFile.delete()
                DownloadTracker.updateProgress(
                    DownloadTaskProgress(
                        taskId = currentTaskId,
                        status = TaskStatus.COMPLETED,
                        progressPercent = 100f,
                        currentTitle = title,
                        savedFilePath = mediaUri?.toString()
                    )
                )
                showCompleteNotification(title)
                stopSelf()
            }.onFailure { error ->
                if (isActive) {
                    Log.e(TAG, "Download failed: ${error.message}", error)
                    DownloadTracker.updateProgress(
                        DownloadTaskProgress(
                            taskId = currentTaskId,
                            status = TaskStatus.FAILED,
                            currentTitle = title,
                            errorMessage = error.message ?: "Download failed"
                        )
                    )
                    showFailedNotification(title, error.message ?: "Download encountered an error")
                }
                stopSelf()
            }
        }
    }

    private fun extractSpeed(line: String): String {
        val match = Regex("""at\s+([0-9.]+\s*[kKmMgG]i?B/s)""").find(line)
        return match?.groupValues?.get(1) ?: "--"
    }

    private fun buildProgressNotification(title: String, progress: Float, statusText: String): android.app.Notification {
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
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Cancel", cancelPendingIntent)
            .build()
    }

    private fun updateNotification(title: String, progress: Float, statusText: String) {
        val notificationManager = getSystemService(NotificationManager::class.java)
        notificationManager?.notify(
            NOTIFICATION_ID,
            buildProgressNotification(title, progress, "${progress.toInt()}% • $statusText")
        )
    }

    private fun showCompleteNotification(title: String) {
        val notificationManager = getSystemService(NotificationManager::class.java)
        val notif = NotificationCompat.Builder(this, OmniApplication.CHANNEL_ID)
            .setContentTitle("Download Complete")
            .setContentText("$title saved to your media library.")
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
