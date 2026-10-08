package com.omni.downloader.data

import com.omni.downloader.data.models.DownloadTaskProgress
import com.omni.downloader.data.models.TaskStatus
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

object DownloadTracker {
    private val _activeTask = MutableStateFlow<DownloadTaskProgress?>(null)
    val activeTask = _activeTask.asStateFlow()

    private val _history = MutableStateFlow<List<DownloadTaskProgress>>(emptyList())
    val history = _history.asStateFlow()

    fun updateProgress(task: DownloadTaskProgress) {
        _activeTask.value = task
        if (task.status == TaskStatus.COMPLETED || task.status == TaskStatus.FAILED || task.status == TaskStatus.CANCELLED) {
            _history.value = listOf(task) + _history.value.filter { it.taskId != task.taskId }
            if (_activeTask.value?.taskId == task.taskId) {
                _activeTask.value = null
            }
        }
    }

    fun removeHistoryItem(taskId: String) {
        _history.value = _history.value.filter { it.taskId != taskId }
    }

    fun clearAllHistory() {
        _history.value = emptyList()
    }
}
