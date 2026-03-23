package com.adrianp.mysteps.phone.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.content.pm.ServiceInfo
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.util.Log
import com.adrianp.mysteps.phone.presentation.MainActivity
import com.adrianp.mysteps.phone.widget.StepWidget
import com.google.android.gms.wearable.DataClient
import com.google.android.gms.wearable.DataEvent
import com.google.android.gms.wearable.DataEventBuffer
import com.google.android.gms.wearable.DataMapItem
import com.google.android.gms.wearable.Wearable
import java.util.Calendar

class PhoneStepService : Service(), DataClient.OnDataChangedListener {

    companion object {
        private const val TAG = "PhoneStepService"
        private const val SERVICE_NOTIFICATION_ID = 1
        private const val ALERT_NOTIFICATION_ID = 2
        private const val SERVICE_CHANNEL_ID = "step_tracking"
        private const val ALERT_CHANNEL_ID = "step_alerts"
        const val PREFS_NAME = "phone_step_prefs"
        const val KEY_HOURLY_STEPS = "hourly_steps"
        const val KEY_STEP_GOAL = "step_goal"
        const val KEY_COMPLETED_HOURS = "completed_hours"
        const val KEY_ELAPSED_HOURS = "elapsed_hours"
        const val KEY_ALARM_ENABLED = "alarm_enabled"
        const val KEY_DISMISSED_HOUR = "dismissed_hour"
        const val KEY_LAST_SYNC = "last_sync"
        const val DEFAULT_STEP_GOAL = 250
        private const val CHECK_INTERVAL_MS = 30_000L
        private const val ALARM_TRIGGER_MINUTE = 50
        const val ACTION_DISMISS = "com.adrianp.mysteps.phone.DISMISS"
        const val ACTION_TEST = "com.adrianp.mysteps.phone.TEST"

        fun getHourlySteps(context: Context): Long {
            return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                .getLong(KEY_HOURLY_STEPS, 0)
        }

        fun getStepGoal(context: Context): Int {
            return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                .getInt(KEY_STEP_GOAL, DEFAULT_STEP_GOAL)
        }

        fun getCompletedHours(context: Context): Int {
            return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                .getInt(KEY_COMPLETED_HOURS, 0)
        }

        fun getElapsedHours(context: Context): Int {
            return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                .getInt(KEY_ELAPSED_HOURS, 0)
        }

        fun isAlarmEnabled(context: Context): Boolean {
            return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                .getBoolean(KEY_ALARM_ENABLED, true)
        }

        fun setAlarmEnabled(context: Context, enabled: Boolean) {
            context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                .edit().putBoolean(KEY_ALARM_ENABLED, enabled).apply()
        }

        fun getLastSync(context: Context): Long {
            return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                .getLong(KEY_LAST_SYNC, 0)
        }
    }

    private lateinit var prefs: SharedPreferences
    private val handler = Handler(Looper.getMainLooper())

    private val checkRunnable = object : Runnable {
        override fun run() {
            checkAlarm()
            handler.postDelayed(this, CHECK_INTERVAL_MS)
        }
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
        startForeground(
            SERVICE_NOTIFICATION_ID,
            buildServiceNotification(),
            ServiceInfo.FOREGROUND_SERVICE_TYPE_HEALTH
        )

        prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        Wearable.getDataClient(this).addListener(this)
        Log.e(TAG, "Service started, listening for watch data")

        handler.postDelayed(checkRunnable, CHECK_INTERVAL_MS)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_DISMISS -> dismissAlert()
            ACTION_TEST -> sendAlertNotification(42, prefs.getInt(KEY_STEP_GOAL, DEFAULT_STEP_GOAL))
        }
        return START_STICKY
    }

    override fun onDataChanged(events: DataEventBuffer) {
        for (event in events) {
            if (event.type == DataEvent.TYPE_CHANGED && event.dataItem.uri.path == "/steps") {
                val dataMap = DataMapItem.fromDataItem(event.dataItem).dataMap
                val hourlySteps = dataMap.getLong("hourly_steps")
                val stepGoal = dataMap.getInt("step_goal")
                val completed = dataMap.getInt("completed_hours")
                val elapsed = dataMap.getInt("elapsed_hours")
                val timestamp = dataMap.getLong("timestamp")

                Log.e(TAG, "Received from watch: steps=$hourlySteps goal=$stepGoal completed=$completed/$elapsed")

                prefs.edit()
                    .putLong(KEY_HOURLY_STEPS, hourlySteps)
                    .putInt(KEY_STEP_GOAL, stepGoal)
                    .putInt(KEY_COMPLETED_HOURS, completed)
                    .putInt(KEY_ELAPSED_HOURS, elapsed)
                    .putLong(KEY_LAST_SYNC, timestamp)
                    .apply()

                StepWidget.updateAll(this)
            }
        }
    }

    private fun checkAlarm() {
        val cal = Calendar.getInstance()
        val minute = cal.get(Calendar.MINUTE)
        val hour = cal.get(Calendar.HOUR_OF_DAY)

        if (!prefs.getBoolean(KEY_ALARM_ENABLED, true)) return
        if (minute < ALARM_TRIGGER_MINUTE) return

        val dismissedHour = prefs.getInt(KEY_DISMISSED_HOUR, -1)
        if (dismissedHour == hour) return

        val hourlySteps = prefs.getLong(KEY_HOURLY_STEPS, 0)
        val stepGoal = prefs.getInt(KEY_STEP_GOAL, DEFAULT_STEP_GOAL)

        if (hourlySteps < stepGoal) {
            sendAlertNotification(hourlySteps, stepGoal)
        }
    }

    private fun sendAlertNotification(steps: Long, goal: Int) {
        val dismissIntent = Intent(this, PhoneStepService::class.java).apply {
            action = ACTION_DISMISS
        }
        val dismissPi = PendingIntent.getService(
            this, 0, dismissIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val openIntent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val openPi = PendingIntent.getActivity(
            this, 0, openIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val remaining = goal - steps
        val notification = Notification.Builder(this, ALERT_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle("🚶 Move! $remaining steps to go")
            .setContentText("You have $steps/$goal steps this hour. Get moving!")
            .setContentIntent(openPi)
            .addAction(Notification.Action.Builder(null, "Dismiss", dismissPi).build())
            .setAutoCancel(true)
            .setCategory(Notification.CATEGORY_REMINDER)
            .build()

        val nm = getSystemService(NotificationManager::class.java)
        nm.notify(ALERT_NOTIFICATION_ID, notification)
    }

    private fun dismissAlert() {
        val hour = Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
        prefs.edit().putInt(KEY_DISMISSED_HOUR, hour).apply()
        val nm = getSystemService(NotificationManager::class.java)
        nm.cancel(ALERT_NOTIFICATION_ID)
    }

    private fun createNotificationChannels() {
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(
            NotificationChannel(SERVICE_CHANNEL_ID, "Step Tracking", NotificationManager.IMPORTANCE_LOW).apply {
                description = "Receiving steps from watch"
                setShowBadge(false)
            }
        )
        nm.createNotificationChannel(
            NotificationChannel(ALERT_CHANNEL_ID, "Step Alerts", NotificationManager.IMPORTANCE_HIGH).apply {
                description = "Alerts when hourly step goal is not met"
                enableVibration(true)
            }
        )
    }

    private fun buildServiceNotification(): Notification {
        val openIntent = Intent(this, MainActivity::class.java)
        val pi = PendingIntent.getActivity(
            this, 0, openIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        return Notification.Builder(this, SERVICE_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_menu_directions)
            .setContentTitle("MySteps")
            .setContentText("Receiving steps from watch")
            .setContentIntent(pi)
            .setOngoing(true)
            .build()
    }

    override fun onDestroy() {
        super.onDestroy()
        handler.removeCallbacks(checkRunnable)
        Wearable.getDataClient(this).removeListener(this)
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
