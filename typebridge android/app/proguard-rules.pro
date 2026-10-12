# ProGuard Rules for TypeBridge Mobile

# Keep OkHttp & Gson models
-keepattributes Signature
-keepattributes *Annotation*
-dontwarn okhttp3.**
-dontwarn okio.**
-keep class com.typebridge.mobile.network.** { *; }

# Keep BouncyCastle Crypto
-keep class org.bouncycastle.** { *; }
-dontwarn org.bouncycastle.**

# Keep Room entities
-keep class com.typebridge.mobile.data.local.** { *; }
