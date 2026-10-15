package com.typebridge.mobile.di

import com.google.gson.Gson
import com.typebridge.mobile.security.TrustManager
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import okhttp3.OkHttpClient
import java.util.concurrent.TimeUnit
import javax.inject.Singleton
import javax.net.ssl.X509TrustManager

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {
    @Provides
    @Singleton
    fun provideGson(): Gson = Gson()

    @Provides
    @Singleton
    fun provideOkHttpClient(trustManager: TrustManager): OkHttpClient {
        val sslFactory = trustManager.getSSLSocketFactory()
        val trustMgr = trustManager.getTrustManagers()
        return OkHttpClient.Builder()
            .sslSocketFactory(sslFactory, trustMgr[0] as X509TrustManager)
            .hostnameVerifier { _, _ -> true }
            .connectTimeout(5, TimeUnit.SECONDS)
            .readTimeout(0, TimeUnit.MILLISECONDS) // No timeout for long-lived WebSocket
            .writeTimeout(10, TimeUnit.SECONDS)
            .pingInterval(3, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .build()
    }
}
