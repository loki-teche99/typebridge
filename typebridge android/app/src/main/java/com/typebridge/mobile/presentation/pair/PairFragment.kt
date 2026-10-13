package com.typebridge.mobile.presentation.pair

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.ProgressBar
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import androidx.navigation.fragment.findNavController
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions
import com.typebridge.mobile.R
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch

@AndroidEntryPoint
class PairFragment : Fragment() {

    private val viewModel: PairViewModel by viewModels()

    private var lastScanTimestamp = 0L

    // Modern sensor-aware QR scanner ActivityResult contract with debouncing
    private val qrScannerLauncher = registerForActivityResult(ScanContract()) { result ->
        val now = System.currentTimeMillis()
        if (now - lastScanTimestamp < 1500L) {
            return@registerForActivityResult // Prevent rapid duplicate pairing triggers
        }
        lastScanTimestamp = now

        if (result != null && !result.contents.isNullOrBlank()) {
            val content = result.contents.trim()
            viewModel.pairFromQr(content)
        }
    }

    // Camera permission contract
    private val cameraPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            startQrScan()
        } else {
            context?.let { ctx ->
                Toast.makeText(
                    ctx,
                    "Camera permission is required to scan QR code. You can also connect manually below.",
                    Toast.LENGTH_LONG
                ).show()
            }
        }
    }

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? = inflater.inflate(R.layout.fragment_pair, container, false)

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val btnScanQr = view.findViewById<Button>(R.id.btnScanQr)
        val editIpAddress = view.findViewById<EditText>(R.id.editIpAddress)
        val editPort = view.findViewById<EditText>(R.id.editPort)
        val editPin = view.findViewById<EditText>(R.id.editPin)
        val btnConnectManual = view.findViewById<Button>(R.id.btnConnectManual)
        val progressBar = view.findViewById<ProgressBar>(R.id.pairingProgressBar)

        btnScanQr.setOnClickListener {
            checkCameraPermissionAndScan()
        }

        btnConnectManual.setOnClickListener {
            val ip = editIpAddress.text.toString().trim()
            val port = editPort.text.toString().toIntOrNull() ?: 8765
            val pin = editPin.text.toString().trim()

            if (ip.isEmpty()) {
                editIpAddress.error = "Please enter desktop IP"
                return@setOnClickListener
            }
            if (pin.length != 6) {
                editPin.error = "Please enter 6-digit PIN"
                return@setOnClickListener
            }

            viewModel.pairManual(ip, port, pin)
        }

        // Observe pairing state
        viewLifecycleOwner.lifecycleScope.launch {
            viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
                launch {
                    viewModel.isPairing.collect { isPairing ->
                        progressBar.visibility = if (isPairing) View.VISIBLE else View.GONE
                        btnScanQr.isEnabled = !isPairing
                        btnConnectManual.isEnabled = !isPairing
                    }
                }

                launch {
                    viewModel.pairResult.collect { result ->
                        if (result?.isSuccess == true) {
                            context?.let { ctx ->
                                Toast.makeText(ctx, "🟢 Paired & Connected to Desktop!", Toast.LENGTH_SHORT).show()
                            }
                            safeNavigateToHome()
                            viewModel.clearResult()
                        } else if (result?.isFailure == true) {
                            val msg = result.exceptionOrNull()?.message ?: "Pairing failed"
                            context?.let { ctx ->
                                Toast.makeText(ctx, "❌ $msg", Toast.LENGTH_LONG).show()
                            }
                            viewModel.clearResult()
                        }
                    }
                }
            }
        }
    }

    private fun checkCameraPermissionAndScan() {
        val context = context ?: return
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            startQrScan()
        } else {
            cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    private fun startQrScan() {
        val options = ScanOptions().apply {
            setCaptureActivity(PortraitCaptureActivity::class.java)
            setPrompt("Align the QR code within the frame\nHold phone in portrait or landscape")
            setBeepEnabled(true)
            setOrientationLocked(false)
            setDesiredBarcodeFormats(ScanOptions.QR_CODE)
            setCameraId(0) // Back camera default
            setTimeout(60000L) // 60s timeout
        }
        qrScannerLauncher.launch(options)
    }

    private fun safeNavigateToHome() {
        try {
            if (isAdded && !isDetached) {
                val navController = findNavController()
                if (navController.currentDestination?.id == R.id.pairFragment) {
                    navController.navigate(R.id.homeFragment)
                }
            }
        } catch (e: Exception) {
            // Guard against rare navigation race conditions
        }
    }
}
