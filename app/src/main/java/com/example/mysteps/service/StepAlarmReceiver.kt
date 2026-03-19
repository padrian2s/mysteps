package com.example.mysteps.service

import android.app.AlarmManager
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.util.Log
import com.example.mysteps.presentation.DismissAlarmActivity
import java.util.Calendar

class StepAlarmReceiver : BroadcastReceiver() {

    companion object {
        private const val TAG = "StepAlarmReceiver"
        const val ACTION_CHECK_STEPS = "com.example.mysteps.CHECK_STEPS_ALARM"
        private const val ALARM_CHANNEL_ID = "step_alarm_channel"
        private const val ALARM_NOTIFICATION_ID = 2

        private const val KEY_SCHEDULED_ALARM_TIME = "scheduled_alarm_time"

        fun scheduleNextAlarm(context: Context) {
            val calendar = Calendar.getInstance()
            val currentMinute = calendar.get(Calendar.MINUTE)

            if (currentMinute >= 50) {
                calendar.add(Calendar.HOUR_OF_DAY, 1)
            }
            calendar.set(Calendar.MINUTE, 50)
            calendar.set(Calendar.SECOND, 0)
            calendar.set(Calendar.MILLISECOND, 0)

            val targetTime = calendar.timeInMillis

            // Don't reschedule if alarm is already set for this exact time
            val prefs = context.getSharedPreferences(StepCounterService.PREFS_NAME, Context.MODE_PRIVATE)
            val currentScheduled = prefs.getLong(KEY_SCHEDULED_ALARM_TIME, 0)
            if (currentScheduled == targetTime) {
                return
            }

            val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
            val intent = Intent(context, StepAlarmReceiver::class.java).apply {
                action = ACTION_CHECK_STEPS
            }
            val pendingIntent = PendingIntent.getBroadcast(
                context, 0, intent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )

            try {
                alarmManager.setExactAndAllowWhileIdle(
                    AlarmManager.RTC_WAKEUP,
                    targetTime,
                    pendingIntent
                )
                prefs.edit().putLong(KEY_SCHEDULED_ALARM_TIME, targetTime).apply()
                Log.e(TAG, "Next alarm scheduled for ${calendar.get(Calendar.HOUR_OF_DAY)}:50")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to schedule alarm", e)
            }
        }

        /**
         * Force reschedule — called from onReceive after alarm fires.
         * Clears saved time so scheduleNextAlarm will actually set a new one.
         */
        fun forceScheduleNextAlarm(context: Context) {
            val prefs = context.getSharedPreferences(StepCounterService.PREFS_NAME, Context.MODE_PRIVATE)
            prefs.edit().putLong(KEY_SCHEDULED_ALARM_TIME, 0).apply()
            scheduleNextAlarm(context)
        }
    }

    override fun onReceive(context: Context, intent: Intent) {
        Log.e(TAG, "Alarm received!")

        val forceTest = intent.getBooleanExtra("force_test", false)
        val prefs = context.getSharedPreferences(StepCounterService.PREFS_NAME, Context.MODE_PRIVATE)

        // Force reschedule for next hour (clears saved time first)
        forceScheduleNextAlarm(context)

        if (!forceTest) {
            val alarmEnabled = prefs.getBoolean(StepCounterService.KEY_ALARM_ENABLED, true)
            val hour = Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
            val intervalStart = prefs.getInt(StepCounterService.KEY_INTERVAL_START, StepCounterService.DEFAULT_INTERVAL_START)
            val intervalEnd = prefs.getInt(StepCounterService.KEY_INTERVAL_END, StepCounterService.DEFAULT_INTERVAL_END)

            if (!alarmEnabled) {
                Log.e(TAG, "Alarm disabled, skipping")
                return
            }
            if (hour < intervalStart || hour >= intervalEnd) {
                Log.e(TAG, "Outside interval ($intervalStart-$intervalEnd), hour=$hour, skipping")
                return
            }
            val dismissedHour = prefs.getInt(StepCounterService.KEY_ALARM_DISMISSED_HOUR, -1)
            if (dismissedHour == hour) {
                Log.e(TAG, "Already dismissed this hour, skipping")
                return
            }
            val hourlySteps = StepCounterService.getHourlySteps(context)
            val stepGoal = prefs.getInt(StepCounterService.KEY_STEP_GOAL, StepCounterService.DEFAULT_STEP_GOAL)
            if (hourlySteps >= stepGoal) {
                Log.e(TAG, "Goal already reached ($hourlySteps >= $stepGoal), skipping")
                return
            }
        } else {
            Log.e(TAG, "Force test mode — bypassing all checks")
        }

        Log.e(TAG, "Triggering alarm!")

        // Vibrate for configured duration
        val durationSeconds = prefs.getInt(StepCounterService.KEY_ALARM_DURATION, StepCounterService.DEFAULT_ALARM_DURATION)
        val vibrator = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
            val vm = context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager
            vm.defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            context.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
        }
        val repeatCount = durationSeconds.coerceAtLeast(1)
        val pattern = LongArray(repeatCount * 2 + 1)
        pattern[0] = 0
        for (i in 0 until repeatCount) {
            pattern[i * 2 + 1] = 500
            pattern[i * 2 + 2] = 500
        }
        vibrator.vibrate(VibrationEffect.createWaveform(pattern, -1))

        // Show notification — tap opens dismiss activity, vibration already running
        showAlarmNotification(context)
    }

    private fun showAlarmNotification(context: Context) {
        val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        val channel = NotificationChannel(
            ALARM_CHANNEL_ID,
            "Step Alarm",
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "Alerts when step goal not reached"
            enableVibration(false)
        }
        notificationManager.createNotificationChannel(channel)

        val dismissIntent = Intent(context, DismissAlarmActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val fullScreenPendingIntent = PendingIntent.getActivity(
            context, 0, dismissIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        // Action to dismiss alarm
        val dismissAction = Notification.Action.Builder(
            android.R.drawable.ic_delete,
            "STOP",
            fullScreenPendingIntent
        ).build()

        val notification = Notification.Builder(context, ALARM_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle("🚶 Move!")
            .setContentText("Step goal not reached")
            .setContentIntent(fullScreenPendingIntent)
            .setFullScreenIntent(fullScreenPendingIntent, true)
            .addAction(dismissAction)
            .setOngoing(true)
            .setCategory(Notification.CATEGORY_ALARM)
            .build()

        notificationManager.notify(ALARM_NOTIFICATION_ID, notification)
    }
}
