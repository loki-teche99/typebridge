package com.typebridge.mobile.presentation.trust

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import com.typebridge.mobile.R
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class TrustFragment : Fragment() {
    private val viewModel: TrustViewModel by viewModels()

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? = inflater.inflate(R.layout.fragment_trust, container, false)
}
