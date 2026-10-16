package com.typebridge.mobile

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.util.Log
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.NavHostFragment
import androidx.navigation.ui.setupWithNavController
import com.google.android.material.bottomnavigation.BottomNavigationView
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private const val TAG = "MainActivity"

@AndroidEntryPoint
class MainActivity : AppCompatActivity() {

    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            Log.d(TAG, "Notification permission granted.")
        } else {
            Log.w(TAG, "Notification permission denied. Background notifications may not be visible.")
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        try {
            val navHostFragment = supportFragmentManager.findFragmentById(R.id.nav_host_fragment) as? NavHostFragment
            val navController = navHostFragment?.navController
            val bottomNav = findViewById<BottomNavigationView>(R.id.bottom_nav)
            if (navController != null && bottomNav != null) {
                bottomNav.setupWithNavController(navController)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error setting up navigation: ${e.message}", e)
        }

        requestNotificationPermission()
        requestBluetoothPermissions()
        handleDeepLinkIntent(intent)
        checkAutoUpdatesOnStartup()
    }

    private var lastAutoCheckTime: Long = 0L

    override fun onResume() {
        super.onResume()
        // Sync Floating Screen Overlay service state
        val prefs = getSharedPreferences("typebridge_prefs", android.content.Context.MODE_PRIVATE)
        val overlayPref = prefs.getBoolean("pref_floating_overlay", false)
        val hasOverlayPerm = android.os.Build.VERSION.SDK_INT < android.os.Build.VERSION_CODES.M || android.provider.Settings.canDrawOverlays(this)
        if (overlayPref && hasOverlayPerm && !com.typebridge.mobile.service.FloatingOverlayService.isRunning) {
            com.typebridge.mobile.service.FloatingOverlayService.start(this)
        }

        val pending = com.typebridge.mobile.updater.UpdateDialogHelper.pendingInstallApk
        if (pending != null && com.typebridge.mobile.updater.AppUpdater.canInstallPackages(this)) {
            com.typebridge.mobile.updater.UpdateDialogHelper.pendingInstallApk = null
            com.typebridge.mobile.updater.AppUpdater.triggerInstall(this, pending)
        } else if (System.currentTimeMillis() - lastAutoCheckTime > 30 * 60 * 1000L) {
            checkAutoUpdatesOnStartup()
        }
    }

    private fun checkAutoUpdatesOnStartup() {
        if (!com.typebridge.mobile.updater.AppUpdater.isAutoCheckEnabled(this)) return
        lastAutoCheckTime = System.currentTimeMillis()
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                delay(1500)
                val result = com.typebridge.mobile.updater.AppUpdater.checkForUpdate(this@MainActivity)
                result.getOrNull()?.let { updateInfo ->
                    withContext(Dispatchers.Main) {
                        com.typebridge.mobile.updater.UpdateDialogHelper.showUpdateAvailableDialog(this@MainActivity, updateInfo)
                    }
                }
            } catch (e: Exception) {
                Log.d(TAG, "Silent auto-update check: ${e.message}")
            }
        }
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleDeepLinkIntent(intent)
    }

    private fun handleDeepLinkIntent(intent: Intent?) {
        val uri = intent?.data ?: return
        if (uri.scheme == "typebridge" && uri.host == "pair") {
            try {
                val navHostFragment = supportFragmentManager.findFragmentById(R.id.nav_host_fragment) as? NavHostFragment
                val navController = navHostFragment?.navController
                // Navigate to pair fragment
                navController?.navigate(R.id.pairFragment)
            } catch (e: Exception) {
                Log.w(TAG, "Could not navigate via deep link: ${e.message}")
            }
        }
    }

    private val bluetoothPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val granted = permissions.entries.all { it.value }
        Log.d(TAG, "Bluetooth permissions: granted=$granted")
    }

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            val hasPermission = ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.POST_NOTIFICATIONS
            ) == PackageManager.PERMISSION_GRANTED

            if (!hasPermission) {
                notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }

    private fun requestBluetoothPermissions() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val needed = mutableListOf<String>()
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED) {
                needed.add(Manifest.permission.BLUETOOTH_CONNECT)
            }
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_SCAN) != PackageManager.PERMISSION_GRANTED) {
                needed.add(Manifest.permission.BLUETOOTH_SCAN)
            }
            if (needed.isNotEmpty()) {
                bluetoothPermissionLauncher.launch(needed.toTypedArray())
            }
        }
    }
}
