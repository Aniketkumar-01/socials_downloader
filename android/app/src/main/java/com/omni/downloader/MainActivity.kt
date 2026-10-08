package com.omni.downloader

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.mutableStateOf
import androidx.core.content.ContextCompat
import com.omni.downloader.ui.screens.MainScreen
import com.omni.downloader.ui.theme.OmniDownloaderTheme

class MainActivity : ComponentActivity() {

    private val sharedUrlState = mutableStateOf<String?>(null)

    private val requestNotificationPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { isGranted ->
            // Notification permission handled
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Handle shared URL from YouTube, Instagram, Reddit, TikTok, Twitter, etc.
        handleIncomingIntent(intent)

        // Request POST_NOTIFICATIONS on Android 13+
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                requestNotificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }

        setContent {
            OmniDownloaderTheme {
                MainScreen(
                    sharedUrl = sharedUrlState.value,
                    onSharedUrlConsumed = {
                        sharedUrlState.value = null
                    }
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIncomingIntent(intent)
    }

    private fun handleIncomingIntent(intent: Intent?) {
        if (intent == null) return
        val url = extractUrlFromIntent(intent)
        if (!url.isNullOrBlank()) {
            sharedUrlState.value = url
        }
    }

    private fun extractUrlFromIntent(intent: Intent): String? {
        // 1. Direct data URI (browser links, VIEW intents)
        intent.dataString?.let { data ->
            val clean = cleanUrl(data)
            if (clean != null) return clean
        }

        // 2. Extra text (YouTube, Instagram, Reddit, TikTok share sheet)
        if (intent.action == Intent.ACTION_SEND) {
            val text = intent.getStringExtra(Intent.EXTRA_TEXT)
            if (!text.isNullOrBlank()) {
                val clean = cleanUrl(text)
                if (clean != null) return clean
            }
        }

        // 3. ClipData
        val clipData = intent.clipData
        if (clipData != null && clipData.itemCount > 0) {
            for (i in 0 until clipData.itemCount) {
                val item = clipData.getItemAt(i)
                val text = item.text?.toString() ?: item.uri?.toString()
                if (!text.isNullOrBlank()) {
                    val clean = cleanUrl(text)
                    if (clean != null) return clean
                }
            }
        }

        return null
    }

    private fun cleanUrl(raw: String): String? {
        val urlRegex = Regex("""https?://[^\s"'<>]+""")
        val match = urlRegex.find(raw) ?: return null
        var url = match.value.trim()
        while (url.isNotEmpty() && url.last() in ".,;!?)]>\"'") {
            url = url.substring(0, url.length - 1)
        }
        return if (url.startsWith("http://") || url.startsWith("https://")) url else null
    }
}
