package com.omni.downloader.data.models

data class QualityOption(
    val id: String,
    val label: String,
    val resolutionLabel: String,
    val isAudioOnly: Boolean = false,
    val estimatedSizeFormatted: String? = null
)

data class PlaylistItem(
    val id: String,
    val title: String,
    val url: String,
    val durationFormatted: String? = null,
    val thumbnail: String? = null,
    val isSelected: Boolean = true
)

data class MediaMetadata(
    val url: String,
    val title: String,
    val channel: String? = null,
    val durationFormatted: String? = null,
    val thumbnail: String? = null,
    val platform: String = "Universal",
    val isPlaylist: Boolean = false,
    val playlistItems: List<PlaylistItem> = emptyList(),
    val availableQualities: List<QualityOption> = listOf(
        QualityOption("best", "Best Available", "Source Maximum", false),
        QualityOption("1080p", "Full HD", "1080p", false),
        QualityOption("720p", "HD Ready", "720p", false),
        QualityOption("480p", "Standard", "480p", false),
        QualityOption("audio_mp3", "Audio Only", "MP3 192kbps", true)
    )
)
