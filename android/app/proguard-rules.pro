# Proguard rules for youtubedl-android and embedded Python JNI
-keep class com.yausername.youtubedl_android.** { *; }
-dontwarn com.yausername.youtubedl_android.**

# Keep models for JSON serialization
-keep class com.omni.downloader.data.models.** { *; }

# Kotlin coroutines and compose rules
-keepclassmembers class kotlinx.coroutines.** { *; }
