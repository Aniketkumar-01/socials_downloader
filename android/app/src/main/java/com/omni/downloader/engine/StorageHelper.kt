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

    fun getAppCookiesFile(context: Context): File {
        return File(context.filesDir, "cookies.txt")
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

        return try {
            val contentValues = ContentValues().apply {
                put(MediaStore.MediaColumns.DISPLAY_NAME, fileName)
                put(MediaStore.MediaColumns.TITLE, title)

                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    val relativeDir = if (isAudio) {
                        "${Environment.DIRECTORY_MUSIC}/OmniDownloader"
                    } else {
                        "${Environment.DIRECTORY_MOVIES}/OmniDownloader"
                    }
                    put(MediaStore.MediaColumns.RELATIVE_PATH, relativeDir)
                    put(MediaStore.MediaColumns.IS_PENDING, 1)
                }

                if (isAudio) {
                    put(MediaStore.MediaColumns.MIME_TYPE, "audio/mpeg")
                } else {
                    put(MediaStore.MediaColumns.MIME_TYPE, "video/mp4")
                }
            }

            val collectionUri = if (isAudio) {
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
