package com.omni.downloader.ui.screens

import android.content.ClipDescription
import android.content.ClipboardManager
import android.content.Context
import android.widget.Toast
import androidx.compose.animation.*
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
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
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.omni.downloader.data.DownloadTracker
import com.omni.downloader.data.models.*
import com.omni.downloader.engine.AppUpdateInfo
import com.omni.downloader.engine.UpdateManager
import com.omni.downloader.engine.YoutubeDLEngine
import com.omni.downloader.service.DownloadForegroundService
import com.omni.downloader.ui.theme.*
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    initialSharedUrl: String? = null
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()

    var urlInput by remember { mutableStateOf(initialSharedUrl ?: "") }
    var isFetching by remember { mutableStateOf(false) }
    var mediaMetadata by remember { mutableStateOf<MediaMetadata?>(null) }
    var selectedQuality by remember { mutableStateOf("best") }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    // Download & Update state
    val activeDownload by DownloadTracker.activeTask.collectAsState()
    val downloadHistory by DownloadTracker.history.collectAsState()
    var showDownloadsSheet by remember { mutableStateOf(false) }
    var showUpdateDialog by remember { mutableStateOf(false) }
    var updateInfo by remember { mutableStateOf<AppUpdateInfo?>(null) }
    var isCheckingUpdate by remember { mutableStateOf(false) }

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
                    // Check Updates Button
                    IconButton(onClick = {
                        coroutineScope.launch {
                            isCheckingUpdate = true
                            val result = UpdateManager.checkForUpdates()
                            result.onSuccess {
                                updateInfo = it
                                showUpdateDialog = true
                            }.onFailure {
                                Toast.makeText(context, "Update check: ${it.message}", Toast.LENGTH_SHORT).show()
                            }
                            isCheckingUpdate = false
                        }
                    }) {
                        if (isCheckingUpdate) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(16.dp),
                                color = AccentCyan,
                                strokeWidth = 2.dp
                            )
                        } else {
                            Icon(
                                Icons.Default.Refresh,
                                contentDescription = "Check for Updates",
                                tint = AccentCyan
                            )
                        }
                    }

                    // Downloads Center Button (with active badge)
                    Box(contentAlignment = Alignment.Center) {
                        IconButton(onClick = { showDownloadsSheet = true }) {
                            Icon(
                                Icons.Default.Download,
                                contentDescription = "Downloads Center",
                                tint = if (activeDownload != null) AccentTeal else TextPrimary
                            )
                        }
                        if (activeDownload != null) {
                            Box(
                                modifier = Modifier
                                    .size(8.dp)
                                    .align(Alignment.TopEnd)
                                    .offset(x = (-6).dp, y = 6.dp)
                                    .clip(CircleShape)
                                    .background(AccentTeal)
                            )
                        }
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

                            // Quality Chips - Uses LazyRow with estimated sizes displayed
                            Text("Select Download Quality:", fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = TextSecondary)
                            Spacer(modifier = Modifier.height(8.dp))

                            LazyRow(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(8.dp),
                                contentPadding = PaddingValues(horizontal = 2.dp)
                            ) {
                                items(meta.availableQualities) { quality ->
                                    val isSelected = quality.id == selectedQuality
                                    FilterChip(
                                        selected = isSelected,
                                        onClick = { selectedQuality = quality.id },
                                        label = {
                                            Row(verticalAlignment = Alignment.CenterVertically) {
                                                Text(
                                                    quality.label,
                                                    fontSize = 12.sp,
                                                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                                    maxLines = 1
                                                )
                                                if (!quality.estimatedSizeFormatted.isNullOrBlank()) {
                                                    Spacer(modifier = Modifier.width(6.dp))
                                                    Surface(
                                                        color = if (isSelected) BgDark.copy(alpha = 0.25f) else AccentTeal.copy(alpha = 0.15f),
                                                        shape = RoundedCornerShape(4.dp)
                                                    ) {
                                                        Text(
                                                            quality.estimatedSizeFormatted,
                                                            fontSize = 10.sp,
                                                            color = if (isSelected) BgDark else AccentTeal,
                                                            fontWeight = FontWeight.SemiBold,
                                                            modifier = Modifier.padding(horizontal = 4.dp, vertical = 1.dp)
                                                        )
                                                    }
                                                }
                                            }
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

                            if (meta.isPlaylist) {
                                Spacer(modifier = Modifier.height(12.dp))
                                Surface(
                                    color = AccentTeal.copy(alpha = 0.12f),
                                    shape = RoundedCornerShape(8.dp),
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    Row(
                                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Icon(Icons.Default.PlaylistPlay, contentDescription = null, tint = AccentTeal, modifier = Modifier.size(20.dp))
                                        Spacer(modifier = Modifier.width(8.dp))
                                        Text(
                                            "Playlist detected • All items will be downloaded in full quality",
                                            color = AccentTeal,
                                            fontSize = 12.sp,
                                            fontWeight = FontWeight.Medium
                                        )
                                    }
                                }
                            }

                            Spacer(modifier = Modifier.height(16.dp))

                            // Download Button
                            val downloadBtnText = if (meta.isPlaylist) "Download Entire Playlist" else "Download to Phone"
                            Button(
                                onClick = {
                                    val isAudio = selectedQuality == "audio_mp3"
                                    DownloadForegroundService.startDownload(
                                        context = context,
                                        url = meta.url,
                                        quality = selectedQuality,
                                        title = meta.title,
                                        isAudio = isAudio,
                                        isPlaylist = meta.isPlaylist
                                    )
                                    val toastMsg = if (meta.isPlaylist) {
                                        "Playlist download started! Tap Downloads icon above to view progress."
                                    } else {
                                        "Download started! Tap Downloads icon above to view progress."
                                    }
                                    Toast.makeText(context, toastMsg, Toast.LENGTH_SHORT).show()
                                },
                                shape = RoundedCornerShape(12.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = AccentTeal),
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(48.dp)
                            ) {
                                Icon(if (meta.isPlaylist) Icons.Default.PlaylistPlay else Icons.Default.Download, contentDescription = null, tint = BgDark)
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(downloadBtnText, fontSize = 15.sp, fontWeight = FontWeight.Bold, color = BgDark)
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

    // Downloads Center Bottom Sheet
    if (showDownloadsSheet) {
        ModalBottomSheet(
            onDismissRequest = { showDownloadsSheet = false },
            containerColor = SurfaceDark,
            contentColor = TextPrimary
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 20.dp, vertical = 8.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.Download, contentDescription = null, tint = AccentTeal)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Downloads Center", fontSize = 18.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                    }
                    IconButton(onClick = { showDownloadsSheet = false }) {
                        Icon(Icons.Default.Close, contentDescription = "Close", tint = TextSecondary)
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))

                // Active Download
                activeDownload?.let { task ->
                    Card(
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = SurfaceCard),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(14.dp)) {
                            val isPaused = task.status == TaskStatus.PAUSED
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    task.currentTitle.ifBlank { "Active Download" },
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = TextPrimary,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                    modifier = Modifier.weight(1f)
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Surface(
                                    color = if (isPaused) AccentCyan.copy(alpha = 0.2f) else AccentTeal.copy(alpha = 0.2f),
                                    shape = RoundedCornerShape(6.dp)
                                ) {
                                    Text(
                                        if (isPaused) "PAUSED" else "DOWNLOADING",
                                        color = if (isPaused) AccentCyan else AccentTeal,
                                        fontSize = 10.sp,
                                        fontWeight = FontWeight.Bold,
                                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                    )
                                }
                            }

                            Spacer(modifier = Modifier.height(10.dp))

                            LinearProgressIndicator(
                                progress = (task.progressPercent / 100f).coerceIn(0f, 1f),
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(6.dp)
                                    .clip(RoundedCornerShape(3.dp)),
                                color = if (isPaused) AccentCyan else AccentTeal,
                                trackColor = BorderSubtle
                            )

                            Spacer(modifier = Modifier.height(8.dp))

                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                val itemProgress = if (task.totalItems > 1) "Item ${task.completedItems} of ${task.totalItems} • " else ""
                                Text(
                                    "$itemProgress${task.progressPercent.toInt()}% • Speed: ${task.speedFormatted}",
                                    fontSize = 11.sp,
                                    color = TextSecondary
                                )
                                Text(
                                    if (task.etaFormatted.isNotBlank()) "ETA: ${task.etaFormatted}" else "",
                                    fontSize = 11.sp,
                                    color = AccentCyan
                                )
                            }

                            Spacer(modifier = Modifier.height(12.dp))

                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(10.dp)
                            ) {
                                if (isPaused) {
                                    Button(
                                        onClick = {
                                            DownloadForegroundService.resumeDownload(context)
                                        },
                                        colors = ButtonDefaults.buttonColors(containerColor = AccentTeal),
                                        shape = RoundedCornerShape(8.dp),
                                        modifier = Modifier
                                            .weight(1f)
                                            .height(38.dp)
                                    ) {
                                        Icon(Icons.Default.PlayArrow, contentDescription = null, tint = BgDark, modifier = Modifier.size(16.dp))
                                        Spacer(modifier = Modifier.width(6.dp))
                                        Text("Resume", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = BgDark)
                                    }
                                } else {
                                    OutlinedButton(
                                        onClick = {
                                            DownloadForegroundService.pauseDownload(context)
                                        },
                                        colors = ButtonDefaults.outlinedButtonColors(contentColor = AccentCyan),
                                        border = BorderStroke(1.dp, AccentCyan.copy(alpha = 0.6f)),
                                        shape = RoundedCornerShape(8.dp),
                                        modifier = Modifier
                                            .weight(1f)
                                            .height(38.dp)
                                    ) {
                                        Icon(Icons.Default.Pause, contentDescription = null, modifier = Modifier.size(16.dp))
                                        Spacer(modifier = Modifier.width(6.dp))
                                        Text("Pause", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                                    }
                                }

                                OutlinedButton(
                                    onClick = {
                                        DownloadForegroundService.cancelDownload(context)
                                    },
                                    colors = ButtonDefaults.outlinedButtonColors(contentColor = StatusError),
                                    border = BorderStroke(1.dp, StatusError.copy(alpha = 0.5f)),
                                    shape = RoundedCornerShape(8.dp),
                                    modifier = Modifier
                                        .weight(1f)
                                        .height(38.dp)
                                ) {
                                    Icon(Icons.Default.Close, contentDescription = null, modifier = Modifier.size(16.dp))
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text("Cancel", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                                }
                            }
                        }
                    }
                    Spacer(modifier = Modifier.height(14.dp))
                }

                // Recent Downloads List
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        "Recent Downloads (${downloadHistory.size})",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = TextSecondary
                    )
                    if (downloadHistory.isNotEmpty()) {
                        TextButton(onClick = { DownloadTracker.clearAllHistory() }) {
                            Text("Clear All", fontSize = 11.sp, color = AccentCyan)
                        }
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))

                if (activeDownload == null && downloadHistory.isEmpty()) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 28.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Icon(
                                Icons.Default.DownloadDone,
                                contentDescription = null,
                                tint = TextSecondary.copy(alpha = 0.4f),
                                modifier = Modifier.size(44.dp)
                            )
                            Spacer(modifier = Modifier.height(8.dp))
                            Text("No active or recent downloads", color = TextSecondary, fontSize = 13.sp)
                        }
                    }
                } else {
                    LazyColumn(
                        modifier = Modifier
                            .fillMaxWidth()
                            .heightIn(max = 280.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        items(downloadHistory) { historyItem ->
                            Card(
                                shape = RoundedCornerShape(10.dp),
                                colors = CardDefaults.cardColors(containerColor = SurfaceCard),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(12.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Icon(
                                        if (historyItem.status == TaskStatus.COMPLETED) Icons.Default.CheckCircle else Icons.Default.Warning,
                                        contentDescription = null,
                                        tint = if (historyItem.status == TaskStatus.COMPLETED) StatusSuccess else StatusError,
                                        modifier = Modifier.size(20.dp)
                                    )
                                    Spacer(modifier = Modifier.width(10.dp))
                                    Column(modifier = Modifier.weight(1f)) {
                                        Text(
                                            historyItem.currentTitle.ifBlank { "Media Item" },
                                            fontSize = 13.sp,
                                            fontWeight = FontWeight.Medium,
                                            color = TextPrimary,
                                            maxLines = 1,
                                            overflow = TextOverflow.Ellipsis
                                        )
                                        Text(
                                            if (historyItem.status == TaskStatus.COMPLETED) "Saved to Media Library" else historyItem.errorMessage ?: "Failed",
                                            fontSize = 11.sp,
                                            color = if (historyItem.status == TaskStatus.COMPLETED) AccentCyan else StatusError
                                        )
                                    }
                                    IconButton(onClick = { DownloadTracker.removeHistoryItem(historyItem.taskId) }) {
                                        Icon(Icons.Default.Delete, contentDescription = "Delete", tint = TextSecondary.copy(alpha = 0.6f), modifier = Modifier.size(16.dp))
                                    }
                                }
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(24.dp))
            }
        }
    }

    // In-App Update Dialog
    if (showUpdateDialog && updateInfo != null) {
        val info = updateInfo!!
        AlertDialog(
            onDismissRequest = { showUpdateDialog = false },
            containerColor = SurfaceDark,
            title = {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        if (info.isUpdateAvailable) Icons.Default.SystemUpdate else Icons.Default.CheckCircle,
                        contentDescription = null,
                        tint = if (info.isUpdateAvailable) AccentTeal else StatusSuccess
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        if (info.isUpdateAvailable) "Update Available" else "OmniDownloader is Up to Date",
                        fontSize = 17.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary
                    )
                }
            },
            text = {
                Column {
                    Text(
                        "Installed: v${info.currentVersion} • Latest: v${info.latestVersion}",
                        fontSize = 12.sp,
                        color = AccentCyan,
                        fontWeight = FontWeight.SemiBold
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                    if (info.isUpdateAvailable) {
                        Text(
                            "What's New:",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            color = TextSecondary
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Card(
                            colors = CardDefaults.cardColors(containerColor = SurfaceCard),
                            shape = RoundedCornerShape(8.dp),
                            modifier = Modifier
                                .fillMaxWidth()
                                .heightIn(max = 140.dp)
                        ) {
                            LazyColumn(modifier = Modifier.padding(10.dp)) {
                                item {
                                    Text(info.releaseNotes, fontSize = 11.sp, color = TextPrimary)
                                }
                            }
                        }
                    } else {
                        Text(
                            "You are running the newest release of OmniDownloader. You can also update the embedded yt-dlp core engine for latest platform fixes.",
                            fontSize = 12.sp,
                            color = TextSecondary
                        )
                    }
                }
            },
            confirmButton = {
                if (info.isUpdateAvailable && info.apkDownloadUrl != null) {
                    Button(
                        onClick = {
                            UpdateManager.openDownloadUrl(context, info.apkDownloadUrl)
                            showUpdateDialog = false
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = AccentTeal)
                    ) {
                        Icon(Icons.Default.Download, contentDescription = null, tint = BgDark, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Download APK", color = BgDark, fontWeight = FontWeight.Bold)
                    }
                } else {
                    Button(
                        onClick = {
                            coroutineScope.launch {
                                Toast.makeText(context, "Updating yt-dlp core...", Toast.LENGTH_SHORT).show()
                                val result = YoutubeDLEngine.updateYtDlpCore(context)
                                result.onSuccess {
                                    Toast.makeText(context, it, Toast.LENGTH_LONG).show()
                                }.onFailure {
                                    Toast.makeText(context, "Update failed: ${it.message}", Toast.LENGTH_SHORT).show()
                                }
                            }
                            showUpdateDialog = false
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = AccentCyan)
                    ) {
                        Text("Update yt-dlp Core", color = BgDark, fontWeight = FontWeight.Bold)
                    }
                }
            },
            dismissButton = {
                TextButton(onClick = { showUpdateDialog = false }) {
                    Text("Close", color = TextSecondary)
                }
            }
        )
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
                error.message ?: "Could not fetch details. Please check the URL and internet connection."
            }
            onError(msg)
        }
    }
}
