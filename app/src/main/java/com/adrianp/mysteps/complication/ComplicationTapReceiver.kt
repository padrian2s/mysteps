package com.adrianp.mysteps.complication

import android.content.BroadcastReceiver
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.util.Log
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceUpdateRequester
import com.adrianp.mysteps.presentation.MainActivity
import com.adrianp.mysteps.service.StepCounterService

class ComplicationTapReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        val steps = StepCounterService.getHourlySteps(context)
        val goal = StepCounterService.getStepGoal(context)

        if (steps >= goal) {
            Log.e("ComplicationTap", "Goal reached, opening app")
            // Double buzz for goal reached
            vibrate(context, longArrayOf(0, 50, 80, 50))
            val activityIntent = Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            }
            context.startActivity(activityIntent)
        } else {
            Log.e("ComplicationTap", "Refreshing complication, steps=$steps goal=$goal")
            // Single short buzz for tap feedback
            vibrate(context, longArrayOf(0, 30))
            try {
                val componentName = ComponentName(context, HourlyStepsComplicationService::class.java)
                ComplicationDataSourceUpdateRequester
                    .create(context = context, complicationDataSourceComponent = componentName)
                    .requestUpdateAll()
            } catch (e: Exception) {
                Log.e("ComplicationTap", "Failed to refresh", e)
            }
        }
    }

    private fun vibrate(context: Context, pattern: LongArray) {
        try {
            val vibrator = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
                val vm = context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager
                vm.defaultVibrator
            } else {
                @Suppress("DEPRECATION")
                context.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
            }
            vibrator.vibrate(VibrationEffect.createWaveform(pattern, -1))
        } catch (e: Exception) {
            Log.e("ComplicationTap", "Failed to vibrate", e)
        }
    }

    companion object {
        const val ACTION_COMPLICATION_TAP = "com.adrianp.mysteps.COMPLICATION_TAP"
    }
}
