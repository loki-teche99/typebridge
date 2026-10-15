package com.typebridge.mobile.presentation.settings

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.google.android.material.button.MaterialButton
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.android.material.switchmaterial.SwitchMaterial
import com.typebridge.mobile.BuildConfig
import com.typebridge.mobile.R
import com.typebridge.mobile.service.FloatingOverlayService
import com.typebridge.mobile.updater.AppUpdater
import com.typebridge.mobile.updater.UpdateDialogHelper
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@AndroidEntryPoint
class SettingsFragment : Fragment() {

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_settings, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val tvVersionLabel = view.findViewById<TextView>(R.id.tvVersionLabel)
        val switchOverlaySettings = view.findViewById<SwitchMaterial>(R.id.switchOverlaySettings)
        val tvOverlayPermHint = view.findViewById<TextView>(R.id.tvOverlayPermHint)
        val switchAutoCheck = view.findViewById<SwitchMaterial>(R.id.switchAutoCheck)
        val btnCheckUpdates = view.findViewById<MaterialButton>(R.id.btnCheckUpdates)
        val layoutUpdateStatus = view.findViewById<View>(R.id.layoutUpdateStatus)
        val pbChecking = view.findViewById<ProgressBar>(R.id.pbChecking)
        val tvUpdateStatus = view.findViewById<TextView>(R.id.tvUpdateStatus)

        // Set version label
        tvVersionLabel.text = "Version ${BuildConfig.VERSION_NAME} (Build ${BuildConfig.VERSION_CODE})"

        // Floating Screen Button Setup
        val prefs = requireContext().getSharedPreferences("typebridge_prefs", Context.MODE_PRIVATE)
        val hasOverlayPerm = Build.VERSION.SDK_INT < Build.VERSION_CODES.M || Settings.canDrawOverlays(requireContext())
        val isOverlayActive = hasOverlayPerm && (FloatingOverlayService.isRunning || prefs.getBoolean("pref_floating_overlay", false))
        switchOverlaySettings.isChecked = isOverlayActive
        tvOverlayPermHint.text = if (hasOverlayPerm) "✅ Permission granted • Ready to float over apps" else "⚠️ Requires 'Display over other apps' permission"

        if (isOverlayActive && !FloatingOverlayService.isRunning) {
            FloatingOverlayService.start(requireContext())
        }

        switchOverlaySettings.setOnCheckedChangeListener { _, isChecked ->
            if (isChecked) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !Settings.canDrawOverlays(requireContext())) {
                    switchOverlaySettings.isChecked = false
                    MaterialAlertDialogBuilder(requireContext())
                        .setTitle("Floating Button Permission")
                        .setMessage("TypeBridge needs the 'Display over other apps' permission so you can move the circular button anywhere on screen and Paste or Type into PC from other apps like WhatsApp and Chrome.\n\nPlease toggle ON 'Allow display over other apps' on the next screen.")
                        .setPositiveButton("Open Settings") { _, _ ->
                            val intent = Intent(
                                Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                                Uri.parse("package:${requireContext().packageName}")
                            )
                            startActivity(intent)
                        }
                        .setNegativeButton("Cancel", null)
                        .show()
                } else {
                    prefs.edit().putBoolean("pref_floating_overlay", true).apply()
                    FloatingOverlayService.start(requireContext())
                    tvOverlayPermHint.text = "✅ Permission granted • Ready to float over apps"
                    Toast.makeText(requireContext(), "✨ Floating Screen Button active! Move it anywhere on screen.", Toast.LENGTH_SHORT).show()
                }
            } else {
                prefs.edit().putBoolean("pref_floating_overlay", false).apply()
                FloatingOverlayService.stop(requireContext())
                Toast.makeText(requireContext(), "Floating Screen Button disabled", Toast.LENGTH_SHORT).show()
            }
        }

        // Load saved preferences
        val context = requireContext()
        switchAutoCheck.isChecked = AppUpdater.isAutoCheckEnabled(context)

        // Save switch toggle
        switchAutoCheck.setOnCheckedChangeListener { _, isChecked ->
            AppUpdater.setAutoCheckEnabled(requireContext(), isChecked)
        }

        // Check for updates button
        btnCheckUpdates.setOnClickListener {
            btnCheckUpdates.isEnabled = false
            layoutUpdateStatus.visibility = View.VISIBLE
            pbChecking.visibility = View.VISIBLE
            tvUpdateStatus.text = "Checking GitHub Releases..."

            viewLifecycleOwner.lifecycleScope.launch(Dispatchers.IO) {
                val result = AppUpdater.checkForUpdate(requireContext(), isManual = true)
                withContext(Dispatchers.Main) {
                    btnCheckUpdates.isEnabled = true
                    pbChecking.visibility = View.GONE

                    result.fold(
                        onSuccess = { updateInfo ->
                            if (updateInfo != null) {
                                tvUpdateStatus.text = "✨ Update available: v${updateInfo.versionName}"
                                UpdateDialogHelper.showUpdateAvailableDialog(requireActivity(), updateInfo)
                            } else {
                                tvUpdateStatus.text = "✅ Up to date (v${BuildConfig.VERSION_NAME})"
                                Toast.makeText(
                                    requireContext(),
                                    "You're on the latest version of TypeBridge (v${BuildConfig.VERSION_NAME})",
                                    Toast.LENGTH_SHORT
                                ).show()
                            }
                        },
                        onFailure = { error ->
                            tvUpdateStatus.text = "❌ Check failed: ${error.message}"
                            MaterialAlertDialogBuilder(requireContext())
                                .setTitle("Update Check Failed")
                                .setMessage("Could not query GitHub Releases: ${error.message}\n\nPlease verify your internet connection.")
                                .setPositiveButton("OK", null)
                                .show()
                        }
                    )
                }
            }
        }

        // Diagnostics export
        val btnExportDiagnostics = view.findViewById<MaterialButton>(R.id.btnExportDiagnostics)
        btnExportDiagnostics?.setOnClickListener {
            val report = buildString {
                appendLine("=== TypeBridge Diagnostic & Support Report ===")
                appendLine("Generated: ${java.util.Date()}")
                appendLine("App Version: ${BuildConfig.VERSION_NAME} (Build ${BuildConfig.VERSION_CODE})")
                appendLine("Android OS: Android ${android.os.Build.VERSION.RELEASE} (API ${android.os.Build.VERSION.SDK_INT})")
                appendLine("Device Model: ${android.os.Build.MANUFACTURER} ${android.os.Build.MODEL}")
                appendLine("Device Architecture: ${android.os.Build.SUPPORTED_ABIS.joinToString(", ")}")
                appendLine("Auto-Update Enabled: ${AppUpdater.isAutoCheckEnabled(requireContext())}")
                appendLine("Canonical Repo: ${AppUpdater.getRepoSlug()}")
                appendLine("Official Website: https://typebridge.42web.io/")
                appendLine("Install Unknown Apps Allowed: ${AppUpdater.canInstallPackages(requireContext())}")
                appendLine("==============================================")
            }
            val clipboard = requireContext().getSystemService(android.content.Context.CLIPBOARD_SERVICE) as? android.content.ClipboardManager
            clipboard?.setPrimaryClip(android.content.ClipData.newPlainText("TypeBridge Diagnostics", report))
            Toast.makeText(requireContext(), "Diagnostics copied to clipboard!", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onResume() {
        super.onResume()
        val switchOverlaySettings = view?.findViewById<SwitchMaterial>(R.id.switchOverlaySettings)
        val tvOverlayPermHint = view?.findViewById<TextView>(R.id.tvOverlayPermHint)
        val prefs = context?.getSharedPreferences("typebridge_prefs", Context.MODE_PRIVATE)
        val hasOverlayPerm = Build.VERSION.SDK_INT < Build.VERSION_CODES.M || (context != null && Settings.canDrawOverlays(context))
        tvOverlayPermHint?.text = if (hasOverlayPerm) "✅ Permission granted • Ready to float over apps" else "⚠️ Requires 'Display over other apps' permission"

        if (hasOverlayPerm && prefs?.getBoolean("pref_floating_overlay", false) == true) {
            context?.let { FloatingOverlayService.start(it) }
            switchOverlaySettings?.isChecked = true
        }
    }
}
