package com.example.mysteps.service

import android.app.Service
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
 * Background service that continuously monitors step count from the device sensor.
 * This service stores step data for hourly tracking.
 */
class StepCounterService : Service(), SensorEventListener {

    companion object {
        private const val TAG = "StepCounterService"
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
        Log.d(TAG, "Service created")

        prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        sensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        stepCounterSensor = sensorManager.getDefaultSensor(Sensor.TYPE_STEP_COUNTER)

        if (stepCounterSensor != null) {
            sensorManager.registerListener(
                this,
                stepCounterSensor,
                SensorManager.SENSOR_DELAY_NORMAL
            )
            Log.d(TAG, "Step counter sensor registered")
        } else {
            Log.e(TAG, "Step counter sensor not available")
        }

        // Initialize currentHour from storage
        val storedHour = prefs.getInt(KEY_CURRENT_HOUR, -1)
        
        if (storedHour == -1) {
            // First time initialization - set to current hour
            // The first sensor reading will initialize the baseline
            val calendar = Calendar.getInstance()
            val currentActualHour = calendar.get(Calendar.HOUR_OF_DAY)
            currentHour = currentActualHour
            Log.d(TAG, "First time initialization for hour: $currentActualHour")
            prefs.edit()
                .putInt(KEY_CURRENT_HOUR, currentActualHour)
                .putLong(KEY_HOUR_START_TIME, calendar.timeInMillis)
                .apply()
        } else {
            // Set currentHour to the stored value
            // If the hour has changed, updateStepCount() will detect it on first sensor reading
            currentHour = storedHour
            Log.d(TAG, "Restored hour from storage: $storedHour")
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return START_STICKY
    }

    override fun onSensorChanged(event: SensorEvent?) {
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

        // Check if we've moved to a new hour
        if (hour != currentHour) {
            Log.d(TAG, "New hour detected: $hour (previous: $currentHour)")
            // Reset baseline for new hour
            prefs.edit()
                .putLong(KEY_HOUR_START_STEPS, totalSteps)
                .putLong(KEY_HOUR_START_TIME, calendar.timeInMillis)
                .putInt(KEY_CURRENT_HOUR, hour)
                .apply()
            currentHour = hour
            Log.d(TAG, "Hour baseline reset to: $totalSteps")
        } else if (!prefs.contains(KEY_HOUR_START_STEPS)) {
            // First sensor reading in current hour - initialize baseline
            Log.d(TAG, "First sensor reading - initializing baseline to: $totalSteps")
            prefs.edit()
                .putLong(KEY_HOUR_START_STEPS, totalSteps)
                .putLong(KEY_HOUR_START_TIME, calendar.timeInMillis)
                .apply()
        }

        // Update current step count
        prefs.edit()
            .putLong(KEY_CURRENT_STEPS, totalSteps)
            .putLong(KEY_LAST_UPDATE, System.currentTimeMillis())
            .apply()

        val hourlySteps = getHourlySteps(this)
        val hourStartSteps = prefs.getLong(KEY_HOUR_START_STEPS, -1)
        Log.d(TAG, "Steps updated - Total: $totalSteps, HourStart: $hourStartSteps, Hourly: $hourlySteps")
    }

    override fun onDestroy() {
        super.onDestroy()
        sensorManager.unregisterListener(this)
        Log.d(TAG, "Service destroyed")
    }

    override fun onBind(intent: Intent?): IBinder? {
        return null
    }
}
