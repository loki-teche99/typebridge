package com.typebridge.mobile.presentation.pair

import com.journeyapps.barcodescanner.CaptureActivity

/**
 * Dedicated CaptureActivity configured with fullSensor orientation handling.
 * Resolves camera sensor coordinate mismatch to enable natural, portrait-first QR scanning
 * without requiring the user to rotate their phone horizontally.
 */
class PortraitCaptureActivity : CaptureActivity()
