package com.typebridge.mobile.presentation.home

import android.content.ClipDescription
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.res.ColorStateList
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.text.Editable
import android.text.TextWatcher
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.InputMethodManager
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.google.android.material.button.MaterialButton
import com.google.android.material.materialswitch.MaterialSwitch
import com.typebridge.mobile.R
import com.typebridge.mobile.domain.model.ConnectionState
import com.typebridge.mobile.service.FloatingOverlayService
import com.typebridge.mobile.utils.JavaCodeFormatter
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch

@AndroidEntryPoint
class HomeFragment : Fragment() {
    companion object {
        const val MODE_JAVA_PERFECT = 0
        const val MODE_IDE = 1
        const val MODE_RAW = 2
    }

    private val viewModel: HomeViewModel by viewModels()
    private var currentMode = MODE_RAW

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? = inflater.inflate(R.layout.fragment_home, container, false)

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val statusDot = view.findViewById<View>(R.id.statusDot)
        val statusText = view.findViewById<TextView>(R.id.statusText)
        val statusDetail = view.findViewById<TextView>(R.id.statusDetail)
        val latencyBadge = view.findViewById<TextView>(R.id.latencyBadge)
        val switchFloatingOverlay = view.findViewById<MaterialSwitch>(R.id.switchFloatingOverlay)
        val editTextInput = view.findViewById<EditText>(R.id.editTextInput)
        val lblCharCount = view.findViewById<TextView>(R.id.lblCharCount)
        val btnPaste = view.findViewById<Button>(R.id.btnPaste)
        val btnClear = view.findViewById<Button>(R.id.btnClear)
        val btnSend = view.findViewById<Button>(R.id.btnSend)
        val btnPause = view.findViewById<Button>(R.id.btnPause)
        val btnResume = view.findViewById<Button>(R.id.btnResume)
        val btnStop = view.findViewById<Button>(R.id.btnStop)
        val btnFormatJava = view.findViewById<Button>(R.id.btnFormatJava)
        val btnModeJava = view.findViewById<MaterialButton>(R.id.btnModeJava)
        val btnModeIde = view.findViewById<MaterialButton>(R.id.btnModeIde)
        val btnModeRaw = view.findViewById<MaterialButton>(R.id.btnModeRaw)

        // Floating Screen Overlay Switch Setup
        val prefs = requireContext().getSharedPreferences("typebridge_prefs", Context.MODE_PRIVATE)
        val hasOverlayPerm = Build.VERSION.SDK_INT < Build.VERSION_CODES.M || Settings.canDrawOverlays(requireContext())
        val isOverlayActive = hasOverlayPerm && (FloatingOverlayService.isRunning || prefs.getBoolean("pref_floating_overlay", false))
        switchFloatingOverlay.isChecked = isOverlayActive
        if (isOverlayActive && !FloatingOverlayService.isRunning) {
            FloatingOverlayService.start(requireContext())
        }

        switchFloatingOverlay.setOnCheckedChangeListener { _, isChecked ->
            if (isChecked) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !Settings.canDrawOverlays(requireContext())) {
                    switchFloatingOverlay.isChecked = false
                    Toast.makeText(
                        requireContext(),
                        "Enable 'Display over other apps' to use TypeBridge floating button",
                        Toast.LENGTH_LONG
                    ).show()
                    val intent = Intent(
                        Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                        Uri.parse("package:${requireContext().packageName}")
                    )
                    startActivity(intent)
                } else {
                    prefs.edit().putBoolean("pref_floating_overlay", true).apply()
                    FloatingOverlayService.start(requireContext())
                    Toast.makeText(
                        requireContext(),
                        "✨ Floating Screen Button active! Tap it anytime to Paste & Type.",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            } else {
                prefs.edit().putBoolean("pref_floating_overlay", false).apply()
                FloatingOverlayService.stop(requireContext())
            }
        }

        // Tap-to-reconnect header
        val statusHeaderClick = View.OnClickListener {
            val state = viewModel.connectionState.value
            if (state !is ConnectionState.Connected) {
                context?.let { ctx ->
                    Toast.makeText(ctx, "🔄 Reconnecting to PC...", Toast.LENGTH_SHORT).show()
                }
                viewModel.reconnectIfDisconnected()
            }
        }
        statusDot.setOnClickListener(statusHeaderClick)
        statusText.setOnClickListener(statusHeaderClick)
        statusDetail.setOnClickListener(statusHeaderClick)

        // Live text counter
        editTextInput.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                val chars = s?.length ?: 0
                val lines = if (chars == 0) 0 else (s?.count { it == '\n' } ?: 0) + 1
                lblCharCount.text = "$chars characters • $lines lines"
            }
            override fun afterTextChanged(s: Editable?) {}
        })

        // Paste from clipboard shortcut with auto-formatting
        btnPaste.setOnClickListener {
            val clipboard = context?.getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
            if (clipboard != null && clipboard.hasPrimaryClip()) {
                val clipData = clipboard.primaryClip
                if (clipData != null && clipData.itemCount > 0) {
                    val rawText = clipData.getItemAt(0).coerceToText(context).toString()
                    if (rawText.isNotEmpty()) {
                        val processed = if (currentMode != MODE_RAW) {
                            JavaCodeFormatter.formatJavaStructure(rawText)
                        } else {
                            JavaCodeFormatter.stripLeadingMargins(rawText)
                        }
                        editTextInput.setText(processed)
                        editTextInput.setSelection(processed.length)
                        context?.let { ctx ->
                            Toast.makeText(ctx, "📋 Pasted & formatted (${processed.length} chars)", Toast.LENGTH_SHORT).show()
                        }
                    }
                }
            }
        }

        // Format Java Code Action Button
        btnFormatJava.setOnClickListener {
            val currentText = editTextInput.text.toString()
            if (currentText.isNotEmpty()) {
                val formatted = JavaCodeFormatter.formatJavaStructure(currentText)
                editTextInput.setText(formatted)
                editTextInput.setSelection(formatted.length)
                context?.let { ctx ->
                    Toast.makeText(ctx, "✨ Formatted with Java 4-space indentation!", Toast.LENGTH_SHORT).show()
                }
            } else {
                context?.let { ctx ->
                    Toast.makeText(ctx, "Paste or type Java code first", Toast.LENGTH_SHORT).show()
                }
            }
        }

        btnClear.setOnClickListener {
            editTextInput.text.clear()
        }

        btnSend.setOnClickListener {
            val raw = editTextInput.text.toString()
            if (raw.isNotEmpty()) {
                val imm = context?.getSystemService(Context.INPUT_METHOD_SERVICE) as? InputMethodManager
                imm?.hideSoftInputFromWindow(view.windowToken, 0)
                val payload = when (currentMode) {
                    MODE_IDE -> JavaCodeFormatter.prepareForIdeMode(raw)
                    MODE_JAVA_PERFECT -> JavaCodeFormatter.formatJavaStructure(raw)
                    else -> raw
                }
                viewModel.sendText(payload)
            } else {
                context?.let { ctx ->
                    Toast.makeText(ctx, "Please enter or paste text to type", Toast.LENGTH_SHORT).show()
                }
            }
        }

        // Mode toggling
        fun updateModeButtons() {
            val ctx = context ?: return
            val activeColor = ContextCompat.getColor(ctx, R.color.tb_primary)
            val transparentColor = ContextCompat.getColor(ctx, android.R.color.transparent)
            val whiteColor = ContextCompat.getColor(ctx, R.color.white)
            val mutedColor = ContextCompat.getColor(ctx, R.color.tb_text_secondary_dark)

            // Mode Java Perfect
            btnModeJava.strokeWidth = if (currentMode == MODE_JAVA_PERFECT) 0 else 2
            btnModeJava.setBackgroundColor(if (currentMode == MODE_JAVA_PERFECT) activeColor else transparentColor)
            btnModeJava.setTextColor(if (currentMode == MODE_JAVA_PERFECT) whiteColor else mutedColor)

            // Mode IDE
            btnModeIde.strokeWidth = if (currentMode == MODE_IDE) 0 else 2
            btnModeIde.setBackgroundColor(if (currentMode == MODE_IDE) activeColor else transparentColor)
            btnModeIde.setTextColor(if (currentMode == MODE_IDE) whiteColor else mutedColor)

            // Mode Raw
            btnModeRaw.strokeWidth = if (currentMode == MODE_RAW) 0 else 2
            btnModeRaw.setBackgroundColor(if (currentMode == MODE_RAW) activeColor else transparentColor)
            btnModeRaw.setTextColor(if (currentMode == MODE_RAW) whiteColor else mutedColor)
        }

        updateModeButtons()

        btnModeJava.setOnClickListener {
            currentMode = MODE_JAVA_PERFECT
            updateModeButtons()
            viewModel.sendControl("MODE_JAVA_PERFECT")
            // Auto-format existing text if present
            val t = editTextInput.text.toString()
            if (t.isNotEmpty()) {
                val formatted = JavaCodeFormatter.formatJavaStructure(t)
                editTextInput.setText(formatted)
                editTextInput.setSelection(formatted.length)
            }
            context?.let { ctx ->
                Toast.makeText(ctx, "📄 Plain / Notepad Full Indentation set", Toast.LENGTH_SHORT).show()
            }
        }

        btnModeIde.setOnClickListener {
            currentMode = MODE_IDE
            updateModeButtons()
            viewModel.sendControl("MODE_IDE")
            context?.let { ctx ->
                Toast.makeText(ctx, "💻 Smart Web IDE (HackerEarth, LeetCode, VS Code) set", Toast.LENGTH_SHORT).show()
            }
        }

        btnModeRaw.setOnClickListener {
            currentMode = MODE_RAW
            updateModeButtons()
            viewModel.sendControl("MODE_RAW")
            context?.let { ctx ->
                Toast.makeText(ctx, "📝 Raw Exact Text Mode set", Toast.LENGTH_SHORT).show()
            }
        }

        btnPause.setOnClickListener {
            viewModel.sendControl("PAUSE")
            context?.let { ctx ->
                Toast.makeText(ctx, "⏸ Pause signal sent", Toast.LENGTH_SHORT).show()
            }
        }

        btnResume.setOnClickListener {
            viewModel.sendControl("RESUME")
            context?.let { ctx ->
                Toast.makeText(ctx, "▶ Resume signal sent", Toast.LENGTH_SHORT).show()
            }
        }

        btnStop.setOnClickListener {
            viewModel.sendControl("STOP")
            context?.let { ctx ->
                Toast.makeText(ctx, "⏹ Stop signal sent to PC", Toast.LENGTH_SHORT).show()
            }
        }

        viewLifecycleOwner.lifecycleScope.launch {
            viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
                launch {
                    viewModel.isSending.collect { isSending ->
                        btnSend.isEnabled = !isSending
                        btnSend.text = if (isSending) "⚡ Streaming to PC..." else "⚡   Send & Type Directly"
                    }
                }

                launch {
                    viewModel.connectionState.collect { state ->
                        val ctx = context ?: return@collect
                        when (state) {
                            is ConnectionState.Connected -> {
                                statusDot.backgroundTintList = ColorStateList.valueOf(
                                    ContextCompat.getColor(ctx, R.color.tb_connected)
                                )
                                statusText.text = "Connected"
                                statusText.setTextColor(ContextCompat.getColor(ctx, R.color.tb_connected))
                                statusDetail.text = state.deviceName
                                latencyBadge.visibility = View.VISIBLE
                                latencyBadge.text = "${state.latencyMs} ms"
                                val badgeColor = when {
                                    state.latencyMs <= 35 -> ContextCompat.getColor(ctx, R.color.tb_connected)
                                    state.latencyMs <= 90 -> ContextCompat.getColor(ctx, R.color.tb_accent_cyan)
                                    else -> ContextCompat.getColor(ctx, R.color.tb_connecting)
                                }
                                latencyBadge.setTextColor(badgeColor)
                            }
                            is ConnectionState.Connecting -> {
                                statusDot.backgroundTintList = ColorStateList.valueOf(
                                    ContextCompat.getColor(ctx, R.color.tb_connecting)
                                )
                                statusText.text = "Connecting..."
                                statusText.setTextColor(ContextCompat.getColor(ctx, R.color.tb_connecting))
                                statusDetail.text = "Bridging to PC..."
                                latencyBadge.visibility = View.GONE
                            }
                            is ConnectionState.Disconnected -> {
                                statusDot.backgroundTintList = ColorStateList.valueOf(
                                    ContextCompat.getColor(ctx, R.color.tb_disconnected)
                                )
                                statusText.text = "Disconnected"
                                statusText.setTextColor(ContextCompat.getColor(ctx, R.color.tb_disconnected))
                                statusDetail.text = "Auto-reconnecting in background..."
                                latencyBadge.visibility = View.GONE
                            }
                            is ConnectionState.Error -> {
                                statusDot.backgroundTintList = ColorStateList.valueOf(
                                    ContextCompat.getColor(ctx, R.color.tb_disconnected)
                                )
                                statusText.text = "Reconnecting"
                                statusText.setTextColor(ContextCompat.getColor(ctx, R.color.tb_disconnected))
                                statusDetail.text = state.message
                                latencyBadge.visibility = View.GONE
                            }
                            is ConnectionState.Reconnecting -> {
                                statusDot.backgroundTintList = ColorStateList.valueOf(
                                    ContextCompat.getColor(ctx, android.R.color.holo_orange_light)
                                )
                                val countText = if (state.maxAttempts > 0) " (${state.attempt}/${state.maxAttempts})" else " (#${state.attempt})"
                                statusText.text = "Reconnecting$countText..."
                                statusText.setTextColor(ContextCompat.getColor(ctx, android.R.color.holo_orange_light))
                                statusDetail.text = "Auto-reconnecting to PC..."
                                latencyBadge.visibility = View.GONE
                            }
                            is ConnectionState.Unstable -> {
                                statusDot.backgroundTintList = ColorStateList.valueOf(
                                    ContextCompat.getColor(ctx, android.R.color.holo_orange_light)
                                )
                                statusText.text = "Unstable Connection"
                                statusText.setTextColor(ContextCompat.getColor(ctx, android.R.color.holo_orange_light))
                                statusDetail.text = state.ip
                                latencyBadge.visibility = View.VISIBLE
                                latencyBadge.text = "${state.latency} ms"
                            }
                        }
                    }
                }

                launch {
                    viewModel.sendResult.collect { result ->
                        if (result?.isSuccess == true) {
                            context?.let { ctx ->
                                Toast.makeText(ctx, "✅ Sent! Desktop typing started.", Toast.LENGTH_SHORT).show()
                            }
                            editTextInput.text.clear()
                            viewModel.clearResult()
                        } else if (result?.isFailure == true) {
                            val err = result.exceptionOrNull()?.message ?: "Failed to send"
                            context?.let { ctx ->
                                Toast.makeText(ctx, "❌ $err", Toast.LENGTH_LONG).show()
                            }
                            viewModel.clearResult()
                        }
                    }
                }

                launch {
                    viewModel.controlResult.collect { result ->
                        if (result?.isFailure == true) {
                            val err = result.exceptionOrNull()?.message ?: "Control failed"
                            context?.let { ctx ->
                                Toast.makeText(ctx, "❌ $err", Toast.LENGTH_SHORT).show()
                            }
                            viewModel.clearResult()
                        }
                    }
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        viewModel.reconnectIfDisconnected()

        // Sync overlay toggle switch if user enabled permission in system settings
        val switchFloatingOverlay = view?.findViewById<MaterialSwitch>(R.id.switchFloatingOverlay)
        val prefs = context?.getSharedPreferences("typebridge_prefs", Context.MODE_PRIVATE)
        val hasOverlayPerm = Build.VERSION.SDK_INT < Build.VERSION_CODES.M || (context != null && Settings.canDrawOverlays(context))
        if (hasOverlayPerm && prefs?.getBoolean("pref_floating_overlay", false) == true) {
            context?.let { FloatingOverlayService.start(it) }
            switchFloatingOverlay?.isChecked = true
        }

        // Pull any text pasted via floating overlay into editor
        val editTextInput = view?.findViewById<EditText>(R.id.editTextInput)
        FloatingOverlayService.lastPastedText?.let { pasted ->
            if (editTextInput != null && editTextInput.text.isEmpty()) {
                editTextInput.setText(pasted)
                editTextInput.setSelection(pasted.length)
            }
            FloatingOverlayService.lastPastedText = null
        }
    }
}
