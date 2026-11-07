package com.adrianp.mysteps.presentation

import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.health.services.client.HealthServices
import androidx.health.services.client.MeasureCallback
import androidx.health.services.client.data.Availability
import androidx.health.services.client.data.DataPointContainer
import androidx.health.services.client.data.DataType
import androidx.health.services.client.data.DeltaDataType
import androidx.health.services.client.unregisterMeasureCallback
import androidx.lifecycle.lifecycleScope
import androidx.wear.compose.material.Text
import kotlinx.coroutines.launch

/** Full-screen live heart rate, opened by tapping the time or the ♥ on the Fluid watch face. */
class HeartRateActivity : ComponentActivity() {

    private var bpm by mutableIntStateOf(0)
    private val measureClient by lazy { HealthServices.getClient(this).measureClient }
    private var registered = false

    private val callback = object : MeasureCallback {
        override fun onAvailabilityChanged(dataType: DeltaDataType<*, *>, availability: Availability) {}

        override fun onDataReceived(data: DataPointContainer) {
            data.getData(DataType.HEART_RATE_BPM).lastOrNull()?.value?.let { value ->
                if (value > 0) bpm = value.toInt()
            }
        }
    }

    private val permissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) startMeasuring()
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { HeartRateScreen(bpm) }
    }

    override fun onStart() {
        super.onStart()
        if (ContextCompat.checkSelfPermission(this, PERMISSION) == PackageManager.PERMISSION_GRANTED) {
            startMeasuring()
        } else {
            permissionLauncher.launch(PERMISSION)
        }
    }

    override fun onStop() {
        super.onStop()
        if (registered) {
            registered = false
            lifecycleScope.launch {
                runCatching { measureClient.unregisterMeasureCallback(DataType.HEART_RATE_BPM, callback) }
            }
        }
    }

    private fun startMeasuring() {
        if (registered) return
        try {
            measureClient.registerMeasureCallback(DataType.HEART_RATE_BPM, callback)
            registered = true
        } catch (e: Exception) {
            Log.e(TAG, "Heart rate measuring failed", e)
        }
    }

    companion object {
        private const val TAG = "HeartRateActivity"
        private val PERMISSION =
            if (Build.VERSION.SDK_INT >= 36) "android.permission.health.READ_HEART_RATE"
            else android.Manifest.permission.BODY_SENSORS
    }
}

private val Red = Color(0xFFE5493F)

@Composable
private fun HeartRateScreen(bpm: Int) {
    // The ♥ beats at the measured rate (one beat per 60/bpm s)
    val beatMs = if (bpm > 0) (60_000 / bpm).coerceIn(300, 1500) else 1000
    val pulse by rememberInfiniteTransition(label = "beat").animateFloat(
        initialValue = 1f,
        targetValue = 1.18f,
        animationSpec = infiniteRepeatable(tween(beatMs / 2, easing = FastOutSlowInEasing), RepeatMode.Reverse),
        label = "scale"
    )
    Box(Modifier.fillMaxSize().background(Color.Black), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
            Text("♥", color = Red, fontSize = 40.sp, modifier = Modifier.scale(pulse))
            Text(
                if (bpm > 0) bpm.toString() else "--",
                color = Red,
                fontSize = 110.sp,
                fontWeight = FontWeight.Light,
                lineHeight = 110.sp
            )
            Text("BPM", color = Red.copy(alpha = 0.7f), fontSize = 18.sp, letterSpacing = 3.sp)
        }
    }
}
