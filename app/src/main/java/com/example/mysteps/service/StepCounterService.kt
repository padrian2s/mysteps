package com.example.mysteps.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.pm.ServiceInfo
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.IBinder
import android.util.Log
import java.util.Calendar

/**
 * Foreground service that continuously monitors step count from the device sensor.
 * Runs as a foreground service to prevent being killed by the system.
 */
class StepCounterService : Service(), SensorEventListener {

    companion object {
        private const val TAG = "StepCounterService"
        private const val NOTIFICATION_ID = 1
        private const val CHANNEL_ID = "step_counter_channel"
        const val PREFS_NAME = "hourly_steps_prefs"
        const val KEY_HOUR_START_STEPS = "hour_start_steps"
        const val KEY_HOUR_START_TIME = "hour_start_time"
        const val KEY_CURRENT_STEPS = "current_steps"
        const val KEY_LAST_UPDATE = "last_update"
        const val KEY_CURRENT_HOUR = "current_hour"

        fun getHourlySteps(context: Context): Long {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            val currentSteps = prefs.getLong(KEY_CURRENT_STEPS, 0)
            val hourStartSteps = prefs.getLong(KEY_HOUR_START_STEPS, 0)
            return kotlin.math.max(0, currentSteps - hourStartSteps)
        }
    }

    private lateinit var sensorManager: SensorManager
    private var stepCounterSensor: Sensor? = null
    private lateinit var prefs: SharedPreferences
    private var currentHour: Int = -1

    override fun onCreate() {
        super.onCreate()
        Log.e(TAG, "Service created")

        createNotificationChannel()
        startForeground(
            NOTIFICATION_ID,
            buildNotification(),
            ServiceInfo.FOREGROUND_SERVICE_TYPE_HEALTH
        )

        prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        sensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        stepCounterSensor = sensorManager.getDefaultSensor(Sensor.TYPE_STEP_COUNTER)

        if (stepCounterSensor != null) {
            sensorManager.registerListener(
                this,
                stepCounterSensor,
                SensorManager.SENSOR_DELAY_NORMAL
            )
            Log.e(TAG, "Step counter sensor registered")
        } else {
            Log.e(TAG, "Step counter sensor not available")
        }

        val storedHour = prefs.getInt(KEY_CURRENT_HOUR, -1)

        if (storedHour == -1) {
            val calendar = Calendar.getInstance()
            val currentActualHour = calendar.get(Calendar.HOUR_OF_DAY)
            currentHour = currentActualHour
            Log.e(TAG, "First time initialization for hour: $currentActualHour")
            prefs.edit()
                .putInt(KEY_CURRENT_HOUR, currentActualHour)
                .putLong(KEY_HOUR_START_TIME, calendar.timeInMillis)
                .apply()
        } else {
            currentHour = storedHour
            Log.e(TAG, "Restored hour from storage: $storedHour")
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return START_STICKY
    }

    override fun onSensorChanged(event: SensorEvent?) {
        Log.e(TAG, "onSensorChanged called, event=$event")
        event?.let {
            if (it.sensor.type == Sensor.TYPE_STEP_COUNTER) {
                val totalSteps = it.values[0].toLong()
                updateStepCount(totalSteps)
            }
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {
        // Not needed for step counter
    }

    private fun updateStepCount(totalSteps: Long) {
        val calendar = Calendar.getInstance()
        val hour = calendar.get(Calendar.HOUR_OF_DAY)

        if (hour != currentHour) {
            Log.e(TAG, "New hour detected: $hour (previous: $currentHour)")
            prefs.edit()
                .putLong(KEY_HOUR_START_STEPS, totalSteps)
                .putLong(KEY_HOUR_START_TIME, calendar.timeInMillis)
                .putInt(KEY_CURRENT_HOUR, hour)
                .apply()
            currentHour = hour
            Log.e(TAG, "Hour baseline reset to: $totalSteps")
        } else if (!prefs.contains(KEY_HOUR_START_STEPS)) {
            Log.e(TAG, "First sensor reading - initializing baseline to: $totalSteps")
            prefs.edit()
                .putLong(KEY_HOUR_START_STEPS, totalSteps)
                .putLong(KEY_HOUR_START_TIME, calendar.timeInMillis)
                .apply()
        }

        prefs.edit()
            .putLong(KEY_CURRENT_STEPS, totalSteps)
            .putLong(KEY_LAST_UPDATE, System.currentTimeMillis())
            .apply()

        val hourlySteps = getHourlySteps(this)
        val hourStartSteps = prefs.getLong(KEY_HOUR_START_STEPS, -1)
        Log.e(TAG, "Steps updated - Total: $totalSteps, HourStart: $hourStartSteps, Hourly: $hourlySteps")
    }

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            "Step Counter",
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "Tracks your hourly steps"
            setShowBadge(false)
        }
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(channel)
    }

    private fun buildNotification(): Notification {
        return Notification.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_menu_directions)
            .setContentTitle("MySteps")
            .setContentText("Tracking steps")
            .setOngoing(true)
            .build()
    }

    override fun onDestroy() {
        super.onDestroy()
        sensorManager.unregisterListener(this)
        Log.e(TAG, "Service destroyed")
    }

    override fun onBind(intent: Intent?): IBinder? {
        return null
    }
}
