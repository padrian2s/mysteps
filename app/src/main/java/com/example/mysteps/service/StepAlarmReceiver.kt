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

/**
 * Schedules ALL alarms for the day at once (one per hour at :50).
 * Each alarm has a unique PendingIntent (request code = hour).
 * No SharedPreferences dependency for scheduling — no race conditions.
 */
class StepAlarmReceiver : BroadcastReceiver() {

    companion object {
        private const val TAG = "StepAlarmReceiver"
        const val ACTION_CHECK_STEPS = "com.example.mysteps.CHECK_STEPS_ALARM"
        private const val ALARM_CHANNEL_ID = "step_alarm_channel"
        private const val ALARM_NOTIFICATION_ID = 2
        private const val EXTRA_ALARM_HOUR = "alarm_hour"

        /**
         * Schedule alarms for ALL hours in the active interval, each at :50.
         * Each hour gets its own PendingIntent (requestCode = hour) so they don't overwrite each other.
         * Safe to call multiple times — AlarmManager replaces identical PendingIntents.
         */
        private const val KEY_LAST_SCHEDULE_DATE = "last_alarm_schedule_date"

        /**
         * Schedule alarms if not already done today.
         * Safe to call from anywhere, as often as you want — only runs once per day.
         */
        fun ensureAlarmsScheduled(context: Context) {
            val prefs = context.getSharedPreferences(StepCounterService.PREFS_NAME, Context.MODE_PRIVATE)
            val today = java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.US).format(java.util.Date())
            val lastDate = prefs.getString(KEY_LAST_SCHEDULE_DATE, "") ?: ""
            if (lastDate == today) return
            scheduleAllAlarms(context)
        }

        /**
         * Schedule ALL alarms for today. One per hour at :50 within the active interval.
         * Each hour gets its own PendingIntent (requestCode = hour).
         */
        fun scheduleAllAlarms(context: Context) {
            val prefs = context.getSharedPreferences(StepCounterService.PREFS_NAME, Context.MODE_PRIVATE)
            val intervalStart = prefs.getInt(StepCounterService.KEY_INTERVAL_START, StepCounterService.DEFAULT_INTERVAL_START)
            val intervalEnd = prefs.getInt(StepCounterService.KEY_INTERVAL_END, StepCounterService.DEFAULT_INTERVAL_END)
            val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager

            val now = Calendar.getInstance()
            val today = Calendar.getInstance()

            var scheduledCount = 0

            for (hour in intervalStart until intervalEnd) {
                today.set(Calendar.HOUR_OF_DAY, hour)
                today.set(Calendar.MINUTE, 50)
                today.set(Calendar.SECOND, 0)
                today.set(Calendar.MILLISECOND, 0)

                // Skip alarms in the past
                if (today.timeInMillis <= now.timeInMillis) continue

                val intent = Intent(context, StepAlarmReceiver::class.java).apply {
                    action = ACTION_CHECK_STEPS
                    putExtra(EXTRA_ALARM_HOUR, hour)
                }
                val pendingIntent = PendingIntent.getBroadcast(
                    context, hour, intent,
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                )

                try {
                    alarmManager.setExactAndAllowWhileIdle(
                        AlarmManager.RTC_WAKEUP,
                        today.timeInMillis,
                        pendingIntent
                    )
                    scheduledCount++
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to schedule alarm for $hour:50", e)
                }
            }

            // Mark today as scheduled
            val todayStr = java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.US).format(java.util.Date())
            prefs.edit().putString(KEY_LAST_SCHEDULE_DATE, todayStr).apply()

            Log.e(TAG, "Scheduled $scheduledCount alarms ($intervalStart:50 - ${intervalEnd - 1}:50)")
        }
    }

    override fun onReceive(context: Context, intent: Intent) {
        val alarmHour = intent.getIntExtra(EXTRA_ALARM_HOUR, -1)
        val now = Calendar.getInstance()
        val hour = now.get(Calendar.HOUR_OF_DAY)
        val min = now.get(Calendar.MINUTE)

        Log.e(TAG, "Alarm received! alarmHour=$alarmHour currentTime=$hour:$min")

        val forceTest = intent.getBooleanExtra("force_test", false)
        val prefs = context.getSharedPreferences(StepCounterService.PREFS_NAME, Context.MODE_PRIVATE)

        // Persistent log
        prefs.edit().putString("last_alarm_fire", "$hour:$min alarmHour=$alarmHour forceTest=$forceTest").apply()

        if (!forceTest) {
            val alarmEnabled = prefs.getBoolean(StepCounterService.KEY_ALARM_ENABLED, true)
            val intervalStart = prefs.getInt(StepCounterService.KEY_INTERVAL_START, StepCounterService.DEFAULT_INTERVAL_START)
            val intervalEnd = prefs.getInt(StepCounterService.KEY_INTERVAL_END, StepCounterService.DEFAULT_INTERVAL_END)

            if (!alarmEnabled) {
                Log.e(TAG, "Alarm disabled, skipping")
                prefs.edit().putString("last_alarm_result", "$hour:$min SKIPPED disabled").apply()
                return
            }
            if (hour < intervalStart || hour >= intervalEnd) {
                Log.e(TAG, "Outside interval ($intervalStart-$intervalEnd), hour=$hour, skipping")
                prefs.edit().putString("last_alarm_result", "$hour:$min SKIPPED outside_interval").apply()
                return
            }
            val dismissedHour = prefs.getInt(StepCounterService.KEY_ALARM_DISMISSED_HOUR, -1)
            if (dismissedHour == hour) {
                Log.e(TAG, "Already dismissed this hour, skipping")
                prefs.edit().putString("last_alarm_result", "$hour:$min SKIPPED dismissed").apply()
                return
            }
            val hourlySteps = StepCounterService.getHourlySteps(context)
            val stepGoal = prefs.getInt(StepCounterService.KEY_STEP_GOAL, StepCounterService.DEFAULT_STEP_GOAL)
            if (hourlySteps >= stepGoal) {
                Log.e(TAG, "Goal already reached ($hourlySteps >= $stepGoal), skipping")
                prefs.edit().putString("last_alarm_result", "$hour:$min SKIPPED goal_reached steps=$hourlySteps goal=$stepGoal").apply()
                return
            }
            prefs.edit().putString("last_alarm_result", "$hour:$min TRIGGERING steps=$hourlySteps goal=$stepGoal").apply()
        } else {
            Log.e(TAG, "Force test mode — bypassing all checks")
            prefs.edit().putString("last_alarm_result", "$hour:$min FORCE_TEST").apply()
        }

        Log.e(TAG, "Triggering alarm!")

        // Vibrate
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

        // Notification
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
