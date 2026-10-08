package com.omni.downloader.ui.screens

import android.content.ClipDescription
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.omni.downloader.data.models.*
import com.omni.downloader.engine.YoutubeDLEngine
import com.omni.downloader.service.DownloadForegroundService
import com.omni.downloader.ui.theme.*
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    initialSharedUrl: String? = null,
    onOpenAuth: () -> Unit
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()

    var urlInput by remember { mutableStateOf(initialSharedUrl ?: "") }
    var isFetching by remember { mutableStateOf(false) }
    var mediaMetadata by remember { mutableStateOf<MediaMetadata?>(null) }
    var selectedQuality by remember { mutableStateOf("best") }
    var activeProgress by remember { mutableStateOf<DownloadTaskProgress?>(null) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    // If initial shared URL arrived via Intent, auto-fetch
    LaunchedEffect(initialSharedUrl) {
        if (!initialSharedUrl.isNullOrBlank()) {
            urlInput = initialSharedUrl
            fetchDetails(context, initialSharedUrl, onStart = { isFetching = true }, onSuccess = {
                mediaMetadata = it
                isFetching = false
            }, onError = {
                errorMessage = it
                isFetching = false
            })
        }
    }

    Scaffold(
        containerColor = BgDark,
        topBar = {
            TopAppBar(
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = SurfaceDark,
                    titleContentColor = TextPrimary
                ),
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(32.dp)
                                .clip(RoundedCornerShape(8.dp))
                                .background(Brush.linearGradient(listOf(AccentTeal, AccentCyan))),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                Icons.Default.Download,
                                contentDescription = null,
                                tint = BgDark,
                                modifier = Modifier.size(20.dp)
                            )
                        }
                        Spacer(modifier = Modifier.width(10.dp))
                        Column {
                            Text(
                                "OmniDownloader",
                                fontSize = 18.sp,
                                fontWeight = FontWeight.Bold,
                                color = TextPrimary
                            )
                            Text(
                                "Universal Media Downloader",
                                fontSize = 11.sp,
                                color = TextSecondary
                            )
                        }
                    }
                },
                actions = {
                    IconButton(onClick = onOpenAuth, modifier = Modifier.padding(end = 4.dp)) {
                        Icon(
                            Icons.Default.Lock,
                            contentDescription = "Cookies & Auth",
                            tint = AccentTeal
                        )
                    }
                }
            )
        }
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            item { Spacer(modifier = Modifier.height(8.dp)) }

            // URL Ingestion Card
            item {
                Card(
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = SurfaceDark),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            "Paste Media URL",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = TextSecondary
                        )
                        Spacer(modifier = Modifier.height(10.dp))

                        OutlinedTextField(
                            value = urlInput,
                            onValueChange = { urlInput = it },
                            placeholder = { Text("https://www.youtube.com/watch?v=...", color = TextSecondary.copy(alpha = 0.6f)) },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = AccentTeal,
                                unfocusedBorderColor = BorderSubtle,
                                focusedTextColor = TextPrimary,
                                unfocusedTextColor = TextPrimary
                            ),
                            trailingIcon = {
                                if (urlInput.isNotBlank()) {
                                    IconButton(onClick = { urlInput = "" }) {
                                        Icon(Icons.Default.Close, contentDescription = "Clear", tint = TextSecondary)
                                    }
                                }
                            }
                        )

                        Spacer(modifier = Modifier.height(12.dp))

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            Button(
                                onClick = {
                                    val clip = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                                    if (clip.hasPrimaryClip() && clip.primaryClipDescription?.hasMimeType(ClipDescription.MIMETYPE_TEXT_PLAIN) == true) {
                                        val text = clip.primaryClip?.getItemAt(0)?.text?.toString() ?: ""
                                        if (text.isNotBlank()) {
                                            urlInput = text.trim()
                                        }
                                    }
                                },
                                shape = RoundedCornerShape(10.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = SurfaceCard),
                                modifier = Modifier.weight(1f)
                            ) {
                                Icon(Icons.Default.ContentPaste, contentDescription = null, tint = AccentCyan, modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(6.dp))
                                Text("Paste", color = TextPrimary)
                            }

                            Button(
                                onClick = {
                                    if (urlInput.isBlank()) {
                                        Toast.makeText(context, "Please paste a URL first", Toast.LENGTH_SHORT).show()
                                        return@Button
                                    }
                                    errorMessage = null
                                    fetchDetails(
                                        context = context,
                                        url = urlInput,
                                        onStart = { isFetching = true },
                                        onSuccess = {
                                            mediaMetadata = it
                                            isFetching = false
                                        },
                                        onError = {
                                            errorMessage = it
                                            isFetching = false
                                        }
                                    )
                                },
                                enabled = !isFetching,
                                shape = RoundedCornerShape(10.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = AccentTeal),
                                modifier = Modifier.weight(1.5f)
                            ) {
                                if (isFetching) {
                                    CircularProgressIndicator(
                                        color = BgDark,
                                        modifier = Modifier.size(18.dp),
                                        strokeWidth = 2.dp
                                    )
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text("Fetching...", color = BgDark, fontWeight = FontWeight.Bold)
                                } else {
                                    Icon(Icons.Default.Search, contentDescription = null, tint = BgDark, modifier = Modifier.size(18.dp))
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text("Fetch Details", color = BgDark, fontWeight = FontWeight.Bold)
                                }
                            }
                        }
                    }
                }
            }

            // Error Notice Banner
            if (errorMessage != null) {
                item {
                    Card(
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = StatusError.copy(alpha = 0.15f)),
                        modifier = Modifier
                            .fillMaxWidth()
                            .border(1.dp, StatusError.copy(alpha = 0.4f), RoundedCornerShape(12.dp))
                    ) {
                        Row(
                            modifier = Modifier.padding(14.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(Icons.Default.Warning, contentDescription = null, tint = StatusError)
                            Spacer(modifier = Modifier.width(10.dp))
                            Text(
                                errorMessage ?: "Unknown error",
                                color = TextPrimary,
                                fontSize = 13.sp,
                                modifier = Modifier.weight(1f)
                            )
                        }
                    }
                }
            }

            // Media Preview Card
            mediaMetadata?.let { meta ->
                item {
                    Card(
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = SurfaceDark),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            // Thumbnail
                            if (!meta.thumbnail.isNullOrBlank()) {
                                Box(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .height(180.dp)
                                        .clip(RoundedCornerShape(12.dp))
                                ) {
                                    AsyncImage(
                                        model = meta.thumbnail,
                                        contentDescription = meta.title,
                                        contentScale = ContentScale.Crop,
                                        modifier = Modifier.fillMaxSize()
                                    )
                                    meta.durationFormatted?.let { dur ->
                                        Surface(
                                            color = BgDark.copy(alpha = 0.85f),
                                            shape = RoundedCornerShape(4.dp),
                                            modifier = Modifier
                                                .align(Alignment.BottomEnd)
                                                .padding(8.dp)
                                        ) {
                                            Text(
                                                dur,
                                                fontSize = 11.sp,
                                                color = TextPrimary,
                                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                            )
                                        }
                                    }
                                }
                                Spacer(modifier = Modifier.height(12.dp))
                            }

                            // Title & Channel
                            Text(
                                meta.title,
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold,
                                color = TextPrimary,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                "${meta.channel ?: "Unknown"} • ${meta.platform}",
                                fontSize = 13.sp,
                                color = AccentCyan
                            )

                            Spacer(modifier = Modifier.height(14.dp))
                            HorizontalDivider(color = BorderSubtle)
                            Spacer(modifier = Modifier.height(14.dp))

                            // Quality Chips
                            Text("Select Download Quality:", fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = TextSecondary)
                            Spacer(modifier = Modifier.height(8.dp))

                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                meta.availableQualities.forEach { quality ->
                                    val isSelected = quality.id == selectedQuality
                                    FilterChip(
                                        selected = isSelected,
                                        onClick = { selectedQuality = quality.id },
                                        label = {
                                            Text(
                                                quality.label,
                                                fontSize = 12.sp,
                                                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal
                                            )
                                        },
                                        colors = FilterChipDefaults.filterChipColors(
                                            selectedContainerColor = AccentTeal,
                                            selectedLabelColor = BgDark,
                                            containerColor = SurfaceCard,
                                            labelColor = TextPrimary
                                        )
                                    )
                                }
                            }

                            Spacer(modifier = Modifier.height(16.dp))

                            // Download Button
                            Button(
                                onClick = {
                                    val isAudio = selectedQuality == "audio_mp3"
                                    DownloadForegroundService.startDownload(
                                        context = context,
                                        url = meta.url,
                                        quality = selectedQuality,
                                        title = meta.title,
                                        isAudio = isAudio
                                    )
                                    Toast.makeText(context, "Download started in background!", Toast.LENGTH_SHORT).show()
                                },
                                shape = RoundedCornerShape(12.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = AccentTeal),
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(48.dp)
                            ) {
                                Icon(Icons.Default.Download, contentDescription = null, tint = BgDark)
                                Spacer(modifier = Modifier.width(8.dp))
                                Text("Download to Phone", fontSize = 15.sp, fontWeight = FontWeight.Bold, color = BgDark)
                            }
                        }
                    }
                }

                // Playlist Items Section
                if (meta.isPlaylist && meta.playlistItems.isNotEmpty()) {
                    item {
                        Card(
                            shape = RoundedCornerShape(16.dp),
                            colors = CardDefaults.cardColors(containerColor = SurfaceDark),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Text(
                                    "Playlist Videos (${meta.playlistItems.size} items)",
                                    fontSize = 15.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = TextPrimary
                                )
                                Spacer(modifier = Modifier.height(10.dp))

                                meta.playlistItems.take(50).forEachIndexed { idx, item ->
                                    Row(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .padding(vertical = 6.dp),
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Text("${idx + 1}.", color = TextSecondary, fontSize = 12.sp, modifier = Modifier.width(24.dp))
                                        Text(
                                            item.title,
                                            color = TextPrimary,
                                            fontSize = 13.sp,
                                            maxLines = 1,
                                            overflow = TextOverflow.Ellipsis,
                                            modifier = Modifier.weight(1f)
                                        )
                                    }
                                    if (idx < meta.playlistItems.size - 1) {
                                        HorizontalDivider(color = BorderSubtle.copy(alpha = 0.5f))
                                    }
                                }
                            }
                        }
                    }
                }
            }

            item { Spacer(modifier = Modifier.height(24.dp)) }
        }
    }
}

private fun fetchDetails(
    context: Context,
    url: String,
    onStart: () -> Unit,
    onSuccess: (MediaMetadata) -> Unit,
    onError: (String) -> Unit
) {
    onStart()
    kotlinx.coroutines.GlobalScope.launch(kotlinx.coroutines.Dispatchers.Main) {
        val result = YoutubeDLEngine.fetchMetadata(context, url)
        result.onSuccess { metadata ->
            onSuccess(metadata)
        }.onFailure { error ->
            val msg = if (error.message?.contains("instance not initialized") == true && com.omni.downloader.OmniApplication.initError != null) {
                "Engine initialization error: ${com.omni.downloader.OmniApplication.initError}"
            } else {
                error.message ?: "Could not fetch details. Check link or sign-in cookies."
            }
            onError(msg)
        }
    }
}
