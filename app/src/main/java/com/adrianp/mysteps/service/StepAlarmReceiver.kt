package com.adrianp.mysteps.service

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import java.util.Calendar

/**
 * Schedules ALL alarms for the day at once (one per hour at :50).
 * Each alarm has a unique PendingIntent (request code = hour).
 * No SharedPreferences dependency for scheduling — no race conditions.
 */
class StepAlarmReceiver : BroadcastReceiver() {

    companion object {
        private const val TAG = "StepAlarmReceiver"
        const val ACTION_CHECK_STEPS = "com.adrianp.mysteps.CHECK_STEPS_ALARM"
        private const val ALARM_CHANNEL_ID = "step_alarm_v2"
        private const val ALARM_NOTIFICATION_ID = 2
        private const val EXTRA_ALARM_HOUR = "alarm_hour"

        private var lastScheduleTimeMs = 0L
        private const val EXTRA_TEST_DELAY = "test_delay_seconds"

        /**
         * Schedule a test alarm N seconds from now.
         */
        fun scheduleTestAlarm(context: Context, delaySeconds: Int) {
            val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
            val intent = Intent(context, StepAlarmReceiver::class.java).apply {
                action = ACTION_CHECK_STEPS
                putExtra("force_test", true)
            }
            val pendingIntent = PendingIntent.getBroadcast(
                context, 99, intent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            val targetMs = System.currentTimeMillis() + delaySeconds * 1000L
            alarmManager.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, targetMs, pendingIntent)
            Log.e(TAG, "Test alarm scheduled in ${delaySeconds}s")
        }

        /**
         * Schedule ALL alarms for today. One per hour at :50 within the active interval.
         * Each hour gets its own PendingIntent (requestCode = hour).
         *
         * IDEMPOTENT: safe to call as often as you want. AlarmManager replaces
         * identical PendingIntents (same requestCode). Throttled to once per minute.
         */
        fun scheduleAllAlarms(context: Context) {
            val currentMs = System.currentTimeMillis()
            if (currentMs - lastScheduleTimeMs < 60_000) return
            lastScheduleTimeMs = currentMs

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
            prefs.edit()
                .putString("last_alarm_result", "$hour:$min TRIGGERING steps=$hourlySteps goal=$stepGoal")
                .putInt(StepCounterService.KEY_ALARM_DISMISSED_HOUR, hour)
                .apply()
        } else {
            Log.e(TAG, "Force test mode — bypassing all checks")
            prefs.edit().putString("last_alarm_result", "$hour:$min FORCE_TEST").apply()
        }

        Log.e(TAG, "Triggering alarm!")

        var vibratedViaService = false

        // Method 1: vibrate via foreground service
        try {
            val vibrateIntent = Intent(context, StepCounterService::class.java).apply {
                action = StepCounterService.ACTION_VIBRATE_ALARM
            }
            context.startService(vibrateIntent)
            vibratedViaService = true
            Log.e(TAG, "Sent vibrate to service OK")
        } catch (e: Exception) {
            Log.e(TAG, "Service vibrate failed: ${e.message}")
        }

        // Method 2: vibrate directly as fallback
        if (!vibratedViaService) {
            try {
                val vibrator = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
                    val vm = context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as android.os.VibratorManager
                    vm.defaultVibrator
                } else {
                    @Suppress("DEPRECATION")
                    context.getSystemService(Context.VIBRATOR_SERVICE) as android.os.Vibrator
                }
                vibrator.vibrate(android.os.VibrationEffect.createOneShot(5000, android.os.VibrationEffect.DEFAULT_AMPLITUDE))
                Log.e(TAG, "Direct vibrate fallback OK")
            } catch (e2: Exception) {
                Log.e(TAG, "Direct vibrate also failed: ${e2.message}")
            }
        }

        // Persistent log
        prefs.edit().putString("last_alarm_vibrate", "$hour:$min viaService=$vibratedViaService").apply()

        // Show notification (also vibrates via channel)
        showAlarmNotification(context)
    }

    private fun showAlarmNotification(context: Context) {
        val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as android.app.NotificationManager

        // Delete old channel that had vibration disabled
        notificationManager.deleteNotificationChannel("step_alarm_channel")

        val channel = android.app.NotificationChannel(
            ALARM_CHANNEL_ID, "Step Alarm", android.app.NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "Step goal not reached"
            enableVibration(true)
            setVibrationPattern(longArrayOf(0, 500, 300, 500, 300, 500, 300, 500, 300, 500))
        }
        notificationManager.createNotificationChannel(channel)

        // Tap notification → open app (shows current steps)
        val appIntent = Intent(context, com.adrianp.mysteps.presentation.MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        val pendingIntent = android.app.PendingIntent.getActivity(
            context, 0, appIntent,
            android.app.PendingIntent.FLAG_UPDATE_CURRENT or android.app.PendingIntent.FLAG_IMMUTABLE
        )

        val notification = android.app.Notification.Builder(context, ALARM_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle("🚶 Move!")
            .setContentText("Step goal not reached")
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setCategory(android.app.Notification.CATEGORY_ALARM)
            .build()

        notificationManager.notify(ALARM_NOTIFICATION_ID, notification)
    }
}
