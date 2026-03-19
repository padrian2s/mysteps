package com.example.mysteps.complication

import android.Manifest
import android.app.PendingIntent
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.drawable.Icon
import androidx.core.content.ContextCompat
import androidx.wear.watchface.complications.data.ComplicationData
import androidx.wear.watchface.complications.data.ComplicationType
import androidx.wear.watchface.complications.data.MonochromaticImage
import androidx.wear.watchface.complications.data.PlainComplicationText
import androidx.wear.watchface.complications.data.RangedValueComplicationData
import androidx.wear.watchface.complications.data.ShortTextComplicationData
import androidx.wear.watchface.complications.datasource.ComplicationRequest
import androidx.wear.watchface.complications.datasource.SuspendingComplicationDataSourceService
import com.example.mysteps.R
import com.example.mysteps.presentation.MainActivity
import com.example.mysteps.service.StepCounterService

class HourlyStepsComplicationService : SuspendingComplicationDataSourceService() {

    override fun getPreviewData(type: ComplicationType): ComplicationData? {
        val goal = StepCounterService.DEFAULT_STEP_GOAL
        return when (type) {
            ComplicationType.RANGED_VALUE -> createRangedComplicationData(
                steps = 180,
                stepGoal = goal,
                completedHours = 3,
                elapsedHours = 5,
                complicationInstanceId = -1
            )
            ComplicationType.SHORT_TEXT -> createShortTextComplicationData(
                steps = 180,
                stepGoal = goal,
                completedHours = 3,
                elapsedHours = 5,
                complicationInstanceId = -1
            )
            else -> null
        }
    }

    override suspend fun onComplicationRequest(request: ComplicationRequest): ComplicationData {
        startStepCounterService()

        if (!hasActivityRecognitionPermission()) {
            return createShortTextComplicationData(
                steps = 0,
                showError = true,
                errorMessage = "No permission",
                complicationInstanceId = request.complicationInstanceId
            )
        }

        val steps = StepCounterService.getHourlySteps(this)
        val goal = StepCounterService.getStepGoal(this)
        val (completed, elapsed) = StepCounterService.getHourlyProgress(this)

        return when (request.complicationType) {
            ComplicationType.RANGED_VALUE -> createRangedComplicationData(
                steps = steps,
                stepGoal = goal,
                completedHours = completed,
                elapsedHours = elapsed,
                complicationInstanceId = request.complicationInstanceId
            )
            else -> createShortTextComplicationData(
                steps = steps,
                stepGoal = goal,
                completedHours = completed,
                elapsedHours = elapsed,
                complicationInstanceId = request.complicationInstanceId
            )
        }
    }

    override fun onComplicationActivated(complicationInstanceId: Int, type: ComplicationType) {
        super.onComplicationActivated(complicationInstanceId, type)
        startStepCounterService()
    }

    private fun startStepCounterService() {
        try {
            val serviceIntent = Intent(this, StepCounterService::class.java)
            startForegroundService(serviceIntent)
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

    private fun buildTapAction(complicationInstanceId: Int): PendingIntent {
        val intent = Intent(this, ComplicationTapReceiver::class.java).apply {
            action = ComplicationTapReceiver.ACTION_COMPLICATION_TAP
        }
        return PendingIntent.getBroadcast(
            this,
            complicationInstanceId,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
    }

    private fun buildText(
        steps: Long,
        stepGoal: Int,
        completedHours: Int,
        elapsedHours: Int,
        showError: Boolean
    ): String {
        return if (showError) {
            "--"
        } else if (steps >= stepGoal) {
            if (elapsedHours > 0) "❤$completedHours/$elapsedHours" else "❤"
        } else {
            steps.toString()
        }
    }

    private fun buildDescription(
        steps: Long,
        stepGoal: Int,
        completedHours: Int,
        elapsedHours: Int,
        showError: Boolean,
        errorMessage: String
    ): String {
        return if (showError) {
            "Steps: $errorMessage"
        } else if (steps >= stepGoal) {
            "Goal reached! $completedHours of $elapsedHours hours completed"
        } else {
            "$steps steps this hour"
        }
    }

    private fun createRangedComplicationData(
        steps: Long,
        stepGoal: Int = StepCounterService.DEFAULT_STEP_GOAL,
        completedHours: Int = 0,
        elapsedHours: Int = 0,
        showError: Boolean = false,
        errorMessage: String = "No data",
        complicationInstanceId: Int
    ): RangedValueComplicationData {
        val text = buildText(steps, stepGoal, completedHours, elapsedHours, showError)
        val description = buildDescription(steps, stepGoal, completedHours, elapsedHours, showError, errorMessage)
        val goalReached = !showError && steps >= stepGoal

        val rangeMin = 0f
        val rangeMax = if (goalReached) 1f else stepGoal.toFloat()
        val rangeValue = if (goalReached) 0f else if (showError) 0f else steps.toFloat().coerceAtMost(stepGoal.toFloat())

        val icon = MonochromaticImage.Builder(
            Icon.createWithResource(this, R.drawable.ic_complication_steps)
        ).build()

        return RangedValueComplicationData.Builder(
            value = rangeValue,
            min = rangeMin,
            max = rangeMax,
            contentDescription = PlainComplicationText.Builder(description).build()
        )
            .setText(PlainComplicationText.Builder(text).build())
            .setMonochromaticImage(icon)
            .setTapAction(buildTapAction(complicationInstanceId))
            .build()
    }

    private fun createShortTextComplicationData(
        steps: Long,
        stepGoal: Int = StepCounterService.DEFAULT_STEP_GOAL,
        completedHours: Int = 0,
        elapsedHours: Int = 0,
        showError: Boolean = false,
        errorMessage: String = "No data",
        complicationInstanceId: Int
    ): ShortTextComplicationData {
        val text = buildText(steps, stepGoal, completedHours, elapsedHours, showError)
        val description = buildDescription(steps, stepGoal, completedHours, elapsedHours, showError, errorMessage)

        val icon = MonochromaticImage.Builder(
            Icon.createWithResource(this, R.drawable.ic_complication_steps)
        ).build()

        return ShortTextComplicationData.Builder(
            text = PlainComplicationText.Builder(text).build(),
            contentDescription = PlainComplicationText.Builder(description).build()
        )
            .setMonochromaticImage(icon)
            .setTapAction(buildTapAction(complicationInstanceId))
            .build()
    }

    companion object {
        const val ACTION_REFRESH_COMPLICATION = "com.example.mysteps.REFRESH_COMPLICATION"
        const val EXTRA_COMPLICATION_ID = "complication_id"
    }
}
