package com.omni.downloader

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import android.util.Log
import com.yausername.youtubedl_android.YoutubeDL
import com.yausername.ffmpeg.FFmpeg
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class OmniApplication : Application() {

    companion object {
        const val CHANNEL_ID = "omni_downloader_channel"
        private const val TAG = "OmniApplication"
        var initError: String? = null
    }

    override fun onCreate() {
        super.onCreate()
        initDownloadEngines()
        createNotificationChannel()
    }

    private fun initDownloadEngines() {
        try {
            // Initialize embedded CPython & yt-dlp native libraries
            YoutubeDL.getInstance().init(this)
            Log.i(TAG, "YoutubeDL engine successfully initialized.")

            // Initialize embedded FFmpeg mobile native binaries
            FFmpeg.getInstance().init(this)
            Log.i(TAG, "Embedded FFmpeg engine successfully initialized.")

            // Quietly update yt-dlp core in background to keep extractors fresh for YouTube, Instagram, Reddit, etc.
            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val status = YoutubeDL.getInstance().updateYoutubeDL(this@OmniApplication)
                    Log.i(TAG, "yt-dlp core background update status: $status")
                } catch (updateErr: Exception) {
                    Log.w(TAG, "yt-dlp core background update check: ${updateErr.message}")
                }
            }
        } catch (e: Exception) {
            initError = e.message ?: e.toString()
            Log.e(TAG, "Failed to initialize embedded download engine: ${e.message}", e)
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val name = getString(R.string.notification_channel_name)
            val descriptionText = getString(R.string.notification_channel_desc)
            val importance = NotificationManager.IMPORTANCE_LOW
            val channel = NotificationChannel(CHANNEL_ID, name, importance).apply {
                description = descriptionText
                setShowBadge(false)
            }
            val notificationManager = getSystemService(NotificationManager::class.java)
            notificationManager?.createNotificationChannel(channel)
        }
    }
}
