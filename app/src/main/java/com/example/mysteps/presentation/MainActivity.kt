/* While this template provides a good starting point for using Wear Compose, you can always
 * take a look at https://github.com/android/wear-os-samples/tree/main/ComposeStarter to find the
 * most up to date changes to the libraries and their usages.
 */

package com.example.mysteps.presentation

import android.content.ComponentName
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.wear.compose.material.MaterialTheme
import androidx.wear.compose.material.Text
import androidx.wear.compose.material.TimeText
import androidx.wear.tooling.preview.devices.WearDevices
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceUpdateRequester
import com.example.mysteps.R
import com.example.mysteps.complication.HourlyStepsComplicationService
import com.example.mysteps.presentation.theme.MyStepsTheme
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()

        super.onCreate(savedInstanceState)

        setTheme(android.R.style.Theme_DeviceDefault)

        // Check if this was triggered by a complication tap
        if (intent?.action == HourlyStepsComplicationService.ACTION_REFRESH_COMPLICATION) {
            val complicationId = intent.getIntExtra(
                HourlyStepsComplicationService.EXTRA_COMPLICATION_ID,
                -1
            )

            if (complicationId != -1) {
                // Request immediate update of the complication
                requestComplicationUpdate(complicationId)
            }

            // Close the activity after triggering the update
            finish()
            return
        }

        setContent {
            WearApp("Android")
        }
    }

    private fun requestComplicationUpdate(complicationId: Int) {
        CoroutineScope(Dispatchers.Main).launch {
            try {
                val componentName = ComponentName(
                    this@MainActivity,
                    HourlyStepsComplicationService::class.java
                )

                ComplicationDataSourceUpdateRequester
                    .create(
                        context = this@MainActivity,
                        complicationDataSourceComponent = componentName
                    )
                    .requestUpdate(complicationId)
            } catch (e: Exception) {
                // Failed to update
            }
        }
    }
}

@Composable
fun WearApp(greetingName: String) {
    MyStepsTheme {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colors.background),
            contentAlignment = Alignment.Center
        ) {
            TimeText()
            Greeting(greetingName = greetingName)
        }
    }
}

@Composable
fun Greeting(greetingName: String) {
    Text(
        modifier = Modifier.fillMaxWidth(),
        textAlign = TextAlign.Center,
        color = MaterialTheme.colors.primary,
        text = stringResource(R.string.hello_world, greetingName)
    )
}

@Preview(device = WearDevices.SMALL_ROUND, showSystemUi = true)
@Composable
fun DefaultPreview() {
    WearApp("Preview Android")
}