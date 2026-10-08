package com.omni.downloader.data.models

enum class TaskStatus {
    IDLE,
    FETCHING,
    DOWNLOADING,
    MERGING,
    COMPLETED,
    FAILED,
    CANCELLED
}

data class DownloadTaskProgress(
    val taskId: String,
    val status: TaskStatus = TaskStatus.IDLE,
    val progressPercent: Float = 0f,
    val downloadedBytes: Long = 0L,
    val totalBytes: Long = 0L,
    val speedFormatted: String = "--",
    val etaFormatted: String = "--",
    val currentTitle: String = "",
    val completedItems: Int = 0,
    val totalItems: Int = 1,
    val savedFilePath: String? = null,
    val errorMessage: String? = null
)
