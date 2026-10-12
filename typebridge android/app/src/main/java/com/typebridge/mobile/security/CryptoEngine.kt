package com.typebridge.mobile.security

import android.util.Base64
import org.bouncycastle.crypto.agreement.X25519Agreement
import org.bouncycastle.crypto.generators.X25519KeyPairGenerator
import org.bouncycastle.crypto.params.X25519KeyGenerationParameters
import org.bouncycastle.crypto.params.X25519PrivateKeyParameters
import org.bouncycastle.crypto.params.X25519PublicKeyParameters
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.Mac
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Handles all cryptographic operations for TypeBridge:
 *  - X25519 key generation (raw 32-byte keys via BouncyCastle)
 *  - HKDF-SHA256 session key derivation (matches the Python desktop)
 *  - AES-256-GCM authenticated encryption / decryption
 *
 * Key format: raw 32-byte keys serialized as Base64 strings (NO X.509 wrapping).
 * This matches the Python cryptography library's X25519PublicKey.public_bytes(Raw, Raw).
 */
@Singleton
class CryptoEngine @Inject constructor() {

    data class KeyPair(
        val privateKey: X25519PrivateKeyParameters,
        val publicKey: X25519PublicKeyParameters
    )

    // ------------------------------------------------------------------ //
    //  Key generation
    // ------------------------------------------------------------------ //

    fun generateKeyPair(): KeyPair {
        val gen = X25519KeyPairGenerator()
        gen.init(X25519KeyGenerationParameters(SecureRandom()))
        val pair = gen.generateKeyPair()
        return KeyPair(
            pair.private as X25519PrivateKeyParameters,
            pair.public as X25519PublicKeyParameters
        )
    }

    /**
     * Serialise a raw X25519 public key to Base64.
     * Produces the same output as Python's pubkey.public_bytes(Raw, Raw) → base64.
     */
    fun serializePublicKey(publicKey: X25519PublicKeyParameters): String =
        Base64.encodeToString(publicKey.encoded, Base64.NO_WRAP)

    /**
     * Deserialise a raw Base64 public key received from the desktop.
     */
    fun deserializePublicKey(b64: String): X25519PublicKeyParameters {
        val raw = Base64.decode(b64.trim(), Base64.DEFAULT)
        return X25519PublicKeyParameters(raw, 0)
    }

    // ------------------------------------------------------------------ //
    //  ECDH + HKDF
    // ------------------------------------------------------------------ //

    /**
     * Perform X25519 key agreement then derive a 32-byte AES key via HKDF-SHA256.
     * Uses info = b"typebridge_handshake" — identical to the Python desktop.
     */
    fun deriveSessionKey(
        myPrivate: X25519PrivateKeyParameters,
        theirPublic: X25519PublicKeyParameters
    ): ByteArray {
        val agreement = X25519Agreement()
        agreement.init(myPrivate)
        val sharedSecret = ByteArray(agreement.agreementSize)
        agreement.calculateAgreement(theirPublic, sharedSecret, 0)
        return hkdfSha256(sharedSecret, salt = null, info = "typebridge_handshake".toByteArray(), length = 32)
    }

    // ------------------------------------------------------------------ //
    //  HKDF-SHA256 (Extract + Expand)
    // ------------------------------------------------------------------ //

    private fun hkdfSha256(
        inputKeyMaterial: ByteArray,
        salt: ByteArray?,
        info: ByteArray,
        length: Int
    ): ByteArray {
        // Extract
        val effectiveSalt = if (salt == null || salt.isEmpty()) ByteArray(32) else salt
        val prk = hmacSha256(effectiveSalt, inputKeyMaterial)

        // Expand
        val result = mutableListOf<Byte>()
        var t = ByteArray(0)
        var counter = 1
        while (result.size < length) {
            t = hmacSha256(prk, t + info + byteArrayOf(counter.toByte()))
            result.addAll(t.toList())
            counter++
        }
        return result.take(length).toByteArray()
    }

    private fun hmacSha256(key: ByteArray, data: ByteArray): ByteArray {
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(key, "HmacSHA256"))
        return mac.doFinal(data)
    }

    // ------------------------------------------------------------------ //
    //  AES-256-GCM
    // ------------------------------------------------------------------ //

    /**
     * Encrypt [plaintext] with AES-256-GCM.
     * Returns Pair(ciphertext_base64, iv_base64).
     */
    fun encrypt(key: ByteArray, plaintext: String): Pair<String, String> {
        if (key.size != 32) {
            throw IllegalArgumentException("Key must be 32 bytes for AES-256 (got ${key.size})")
        }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        val iv = ByteArray(12).also { SecureRandom().nextBytes(it) }
        cipher.init(Cipher.ENCRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(128, iv))
        val ciphertext = cipher.doFinal(plaintext.toByteArray(Charsets.UTF_8))
        return Pair(
            Base64.encodeToString(ciphertext, Base64.NO_WRAP),
            Base64.encodeToString(iv, Base64.NO_WRAP)
        )
    }

    /**
     * Decrypt an AES-256-GCM ciphertext.
     */
    fun decrypt(key: ByteArray, ciphertextB64: String, ivB64: String): String {
        if (key.size != 32) {
            throw IllegalArgumentException("Key must be 32 bytes for AES-256 (got ${key.size})")
        }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        val iv = Base64.decode(ivB64.trim(), Base64.DEFAULT)
        val ct = Base64.decode(ciphertextB64.trim(), Base64.DEFAULT)
        cipher.init(Cipher.DECRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(128, iv))
        return String(cipher.doFinal(ct), Charsets.UTF_8)
    }
}
