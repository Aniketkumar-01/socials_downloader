package com.omni.downloader

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import com.omni.downloader.ui.screens.MainScreen
import com.omni.downloader.ui.screens.WebViewAuthActivity
import com.omni.downloader.ui.theme.OmniDownloaderTheme

class MainActivity : ComponentActivity() {

    private var sharedUrl: String? = null

    private val requestNotificationPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { isGranted ->
            // Notification permission handled
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Handle shared URL from YouTube, Instagram, or TikTok app
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
                    initialSharedUrl = sharedUrl,
                    onOpenAuth = {
                        startActivity(Intent(this, WebViewAuthActivity::class.java))
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
        if (intent?.action == Intent.ACTION_SEND && intent.type == "text/plain") {
            val text = intent.getStringExtra(Intent.EXTRA_TEXT)
            if (!text.isNullOrBlank()) {
                // Extract URL from shared text (e.g., YouTube app shares "Check this out: https://youtu.be/...")
                val urlRegex = Regex("""https?://\S+""")
                val match = urlRegex.find(text)
                sharedUrl = match?.value ?: text.trim()
            }
        }
    }
}
