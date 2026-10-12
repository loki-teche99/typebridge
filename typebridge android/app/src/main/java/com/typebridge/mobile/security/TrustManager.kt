package com.typebridge.mobile.security

import javax.inject.Inject
import javax.inject.Singleton
import javax.net.ssl.SSLContext
import javax.net.ssl.SSLSocketFactory
import javax.net.ssl.TrustManager
import javax.net.ssl.X509TrustManager
import java.security.cert.X509Certificate

/**
 * Custom TrustManager that accepts any TLS certificate.
 * This is intentional for local LAN / hotspot connections to the TypeBridge Desktop
 * which uses a self-signed certificate. The application-layer AES-256-GCM
 * encryption and ECDH key exchange provide the real security guarantee.
 *
 * DO NOT use this trust manager for any internet connections.
 */
@Singleton
class TrustManager @Inject constructor() : X509TrustManager {

    override fun checkClientTrusted(chain: Array<out X509Certificate>?, authType: String?) {
        // Accept any client cert (local LAN only)
    }

    override fun checkServerTrusted(chain: Array<out X509Certificate>?, authType: String?) {
        // Accept any server cert (local LAN only — security is at app layer)
        // TODO: In a future version, pin the fingerprint stored during pairing
    }

    override fun getAcceptedIssuers(): Array<X509Certificate> = arrayOf()

    /**
     * Build an SSLSocketFactory that uses this trust manager.
     */
    fun getSSLSocketFactory(): SSLSocketFactory {
        val sslContext = SSLContext.getInstance("TLS")
        sslContext.init(null, arrayOf<TrustManager>(this), java.security.SecureRandom())
        return sslContext.socketFactory
    }

    /**
     * Returns the TrustManager array for use with OkHttpClient.
     */
    fun getTrustManagers(): Array<TrustManager> = arrayOf(this)
}
