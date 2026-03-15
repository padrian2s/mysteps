package com.example.mysteps.complication

import android.content.BroadcastReceiver
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.util.Log
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceUpdateRequester
import com.example.mysteps.presentation.MainActivity
import com.example.mysteps.service.StepCounterService

/**
 * Handles complication tap: if goal reached, opens the app settings.
 * If goal not reached, just requests a complication data refresh.
 */
class ComplicationTapReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        val steps = StepCounterService.getHourlySteps(context)
        val goal = StepCounterService.getStepGoal(context)

        if (steps >= goal) {
            // Goal reached — open the settings app
            Log.e("ComplicationTap", "Goal reached, opening app")
            val activityIntent = Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            }
            context.startActivity(activityIntent)
        } else {
            // Goal not reached — just refresh the complication
            Log.e("ComplicationTap", "Refreshing complication, steps=$steps goal=$goal")
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

    companion object {
        const val ACTION_COMPLICATION_TAP = "com.example.mysteps.COMPLICATION_TAP"
    }
}
