package com.omni.downloader.engine

import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.util.Log
import java.io.File
import java.io.FileInputStream

object StorageHelper {
    private const val TAG = "StorageHelper"

    fun getTempDownloadDir(context: Context): File {
        val dir = File(context.cacheDir, "omni_downloads")
        if (!dir.exists()) dir.mkdirs()
        return dir
    }

    /**
     * Publishes a completed temporary media file into Android's public MediaStore
     * so it immediately appears in the user's Gallery, VLC, Files, and Music apps.
     */
    fun saveToPublicMedia(
        context: Context,
        sourceFile: File,
        title: String,
        isAudio: Boolean
    ): Uri? {
        if (!sourceFile.exists()) {
            Log.e(TAG, "Source file does not exist: ${sourceFile.absolutePath}")
            return null
        }

        val resolver = context.contentResolver
        val fileName = sourceFile.name

        val ext = sourceFile.extension.lowercase()
        val isAudioActual = isAudio || ext in setOf("mp3", "m4a", "opus", "flac", "wav", "aac", "ogg")
        val mimeType = when (ext) {
            "mp3" -> "audio/mpeg"
            "m4a" -> "audio/mp4"
            "opus" -> "audio/opus"
            "flac" -> "audio/flac"
            "wav" -> "audio/wav"
            "aac" -> "audio/aac"
            "ogg" -> "audio/ogg"
            "webm" -> if (isAudioActual) "audio/webm" else "video/webm"
            "mkv" -> "video/x-matroska"
            "mp4" -> "video/mp4"
            else -> if (isAudioActual) "audio/mpeg" else "video/mp4"
        }

        return try {
            val contentValues = ContentValues().apply {
                put(MediaStore.MediaColumns.DISPLAY_NAME, fileName)
                put(MediaStore.MediaColumns.TITLE, title)

                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    val relativeDir = if (isAudioActual) {
                        "${Environment.DIRECTORY_MUSIC}/OmniDownloader"
                    } else {
                        "${Environment.DIRECTORY_MOVIES}/OmniDownloader"
                    }
                    put(MediaStore.MediaColumns.RELATIVE_PATH, relativeDir)
                    put(MediaStore.MediaColumns.IS_PENDING, 1)
                }

                put(MediaStore.MediaColumns.MIME_TYPE, mimeType)
            }

            val collectionUri = if (isAudioActual) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    MediaStore.Audio.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
                } else {
                    MediaStore.Audio.Media.EXTERNAL_CONTENT_URI
                }
            } else {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    MediaStore.Video.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
                } else {
                    MediaStore.Video.Media.EXTERNAL_CONTENT_URI
                }
            }

            val destinationUri = resolver.insert(collectionUri, contentValues)
                ?: throw IllegalStateException("Failed to create MediaStore entry")

            // Copy file stream
            resolver.openOutputStream(destinationUri)?.use { outStream ->
                FileInputStream(sourceFile).use { inStream ->
                    inStream.copyTo(outStream)
                }
            }

            // Mark pending false on Android 10+ so other apps can immediately see it
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                contentValues.clear()
                contentValues.put(MediaStore.MediaColumns.IS_PENDING, 0)
                resolver.update(destinationUri, contentValues, null, null)
            }

            Log.i(TAG, "Successfully exported media to MediaStore: $destinationUri")
            destinationUri
        } catch (e: Exception) {
            Log.e(TAG, "Failed to save media to MediaStore: ${e.message}", e)
            null
        }
    }
}
