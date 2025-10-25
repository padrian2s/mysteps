package com.example.mysteps.complication

import android.Manifest
import android.app.PendingIntent
import android.content.ComponentName
import android.content.Intent
import android.content.pm.PackageManager
import androidx.core.content.ContextCompat
import androidx.wear.watchface.complications.data.ComplicationData
import androidx.wear.watchface.complications.data.ComplicationType
import androidx.wear.watchface.complications.data.PlainComplicationText
import androidx.wear.watchface.complications.data.ShortTextComplicationData
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceUpdateRequester
import androidx.wear.watchface.complications.datasource.ComplicationRequest
import androidx.wear.watchface.complications.datasource.SuspendingComplicationDataSourceService
import com.example.mysteps.presentation.MainActivity
import com.example.mysteps.service.StepCounterService

/**
 * Complication data source that displays the number of steps taken in the current hour.
 *
 * This complication reads step data from the StepCounterService which continuously
 * monitors the device's step counter sensor.
 *
 * Tap the complication to refresh the step count immediately.
 */
class HourlyStepsComplicationService : SuspendingComplicationDataSourceService() {

    override fun getPreviewData(type: ComplicationType): ComplicationData? {
        if (type != ComplicationType.SHORT_TEXT) {
            return null
        }
        return createComplicationData(steps = 1234, complicationInstanceId = -1)
    }

    override suspend fun onComplicationRequest(request: ComplicationRequest): ComplicationData {
        // Start the step counter service if it's not already running
        startStepCounterService()

        // Check if we have the required permission
        if (!hasActivityRecognitionPermission()) {
            return createComplicationData(
                steps = 0,
                showError = true,
                errorMessage = "No permission",
                complicationInstanceId = request.complicationInstanceId
            )
        }

        // Get hourly steps from the service's shared preferences
        val steps = StepCounterService.getHourlySteps(this)
        return createComplicationData(
            steps = steps,
            complicationInstanceId = request.complicationInstanceId
        )
    }

    override fun onComplicationActivated(complicationInstanceId: Int, type: ComplicationType) {
        super.onComplicationActivated(complicationInstanceId, type)
        // Ensure service is running when complication is activated
        startStepCounterService()
    }

    private fun startStepCounterService() {
        try {
            val serviceIntent = Intent(this, StepCounterService::class.java)
            startService(serviceIntent)
        } catch (e: Exception) {
            // Service already running or failed to start
        }
    }

    private fun hasActivityRecognitionPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.ACTIVITY_RECOGNITION
        ) == PackageManager.PERMISSION_GRANTED
    }

    private fun createComplicationData(
        steps: Long,
        showError: Boolean = false,
        errorMessage: String = "No data",
        complicationInstanceId: Int
    ): ShortTextComplicationData {
        val text = if (showError) {
            "--"
        } else if (steps >= 250) {
            "❤"
        } else {
            steps.toString()
        }

        val contentDescription = if (showError) {
            "Steps: $errorMessage"
        } else if (steps >= 250) {
            "$steps steps this hour - Goal reached!"
        } else {
            "$steps steps this hour"
        }

        // Create intent to open MainActivity and trigger complication update
        val intent = Intent(this, MainActivity::class.java).apply {
            action = ACTION_REFRESH_COMPLICATION
            putExtra(EXTRA_COMPLICATION_ID, complicationInstanceId)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }

        val pendingIntent = PendingIntent.getActivity(
            this,
            complicationInstanceId,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        return ShortTextComplicationData.Builder(
            text = PlainComplicationText.Builder(text).build(),
            contentDescription = PlainComplicationText.Builder(contentDescription).build()
        )
            .setTapAction(pendingIntent)
            .build()
    }

    companion object {
        const val ACTION_REFRESH_COMPLICATION = "com.example.mysteps.REFRESH_COMPLICATION"
        const val EXTRA_COMPLICATION_ID = "complication_id"
    }
}
