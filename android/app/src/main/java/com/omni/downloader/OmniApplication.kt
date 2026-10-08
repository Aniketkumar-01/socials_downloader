package com.omni.downloader

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import android.util.Log
import com.yausername.youtubedl_android.YoutubeDL
import com.yausername.ffmpeg.FFmpeg

class OmniApplication : Application() {

    companion object {
        const val CHANNEL_ID = "omni_downloader_channel"
        private const val TAG = "OmniApplication"
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
        } catch (e: Exception) {
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
