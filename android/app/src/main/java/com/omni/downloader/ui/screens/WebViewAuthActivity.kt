package com.omni.downloader.ui.screens

import android.annotation.SuppressLint
import android.os.Bundle
import android.webkit.CookieManager
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView
import com.omni.downloader.engine.StorageHelper
import com.omni.downloader.ui.theme.OmniDownloaderTheme
import java.io.File

class WebViewAuthActivity : ComponentActivity() {

    private var currentUrl = "https://accounts.google.com/signin"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val targetUrl = intent.getStringExtra("EXTRA_AUTH_URL") ?: currentUrl
        currentUrl = targetUrl

        setContent {
            OmniDownloaderTheme {
                AuthScreen(
                    url = currentUrl,
                    onBack = { finish() },
                    onSaveCookies = { saveCurrentCookies() }
                )
            }
        }
    }

    private fun saveCurrentCookies() {
        val cookieManager = CookieManager.getInstance()
        val cookiesString = cookieManager.getCookie(currentUrl)

        if (cookiesString.isNullOrBlank()) {
            Toast.makeText(this, "No cookies detected. Please complete sign-in first.", Toast.LENGTH_SHORT).show()
            return
        }

        try {
            val cookiesFile = StorageHelper.getAppCookiesFile(this)
            // Parse and format to Netscape format or simple headers
            val netscapeHeader = "# Netscape HTTP Cookie File\n# Exported from OmniDownloader Mobile WebView\n"
            val sb = StringBuilder(netscapeHeader)

            cookiesString.split(";").forEach { pair ->
                val trimmed = pair.trim()
                val eqIdx = trimmed.indexOf('=')
                if (eqIdx != -1) {
                    val name = trimmed.substring(0, eqIdx)
                    val value = trimmed.substring(eqIdx + 1)
                    val domain = if (currentUrl.contains("youtube.com")) ".youtube.com" else ".google.com"
                    sb.append("$domain\tTRUE\t/\tTRUE\t2147483647\t$name\t$value\n")
                }
            }

            cookiesFile.writeText(sb.toString())
            Toast.makeText(this, "Cookies saved! YouTube bot bypass active.", Toast.LENGTH_LONG).show()
            finish()
        } catch (e: Exception) {
            Toast.makeText(this, "Failed to save cookies: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@SuppressLint("SetJavaScriptEnabled")
@Composable
fun AuthScreen(
    url: String,
    onBack: () -> Unit,
    onSaveCookies: () -> Unit
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Sign In & Save Cookies") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(onClick = onSaveCookies) {
                        Icon(Icons.Default.Check, contentDescription = "Save Cookies")
                    }
                }
            )
        }
    ) { padding ->
        AndroidView(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            factory = { context ->
                WebView(context).apply {
                    settings.javaScriptEnabled = true
                    settings.domStorageEnabled = true
                    webViewClient = WebViewClient()
                    loadUrl(url)
                }
            }
        )
    }
}
