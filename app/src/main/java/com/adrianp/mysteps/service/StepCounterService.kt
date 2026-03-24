package com.adrianp.mysteps.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.BroadcastReceiver
import android.content.ComponentName
import android.content.pm.ServiceInfo
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.SharedPreferences
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.util.Log
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceUpdateRequester
import com.adrianp.mysteps.complication.HourlyStepsComplicationService
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale

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
        const val KEY_STEP_GOAL = "step_goal"
        const val KEY_ALARM_ENABLED = "alarm_enabled"
        const val KEY_ALARM_DISMISSED_HOUR = "alarm_dismissed_hour"
        const val KEY_INTERVAL_START = "interval_start_hour"
        const val KEY_INTERVAL_END = "interval_end_hour"
        const val KEY_COMPLETED_HOURS = "completed_hours"
        const val KEY_COMPLETED_HOURS_DATE = "completed_hours_date"
        const val DEFAULT_STEP_GOAL = 250
        const val DEFAULT_INTERVAL_START = 8
        const val DEFAULT_INTERVAL_END = 21
        const val KEY_ALARM_DURATION = "alarm_duration_seconds"
        const val DEFAULT_ALARM_DURATION = 10
        const val KEY_STEP_OFFSET = "step_offset"
        const val DEFAULT_STEP_OFFSET = 0
        const val ACTION_DISMISS_ALARM = "com.adrianp.mysteps.DISMISS_ALARM"
        const val ACTION_VIBRATE_ALARM = "com.adrianp.mysteps.VIBRATE_ALARM"
        private const val ALARM_CHECK_INTERVAL_MS = 30_000L
        private const val ALARM_TRIGGER_MINUTE = 50
        private const val SCREEN_ON_UPDATE_INTERVAL_MS = 2_000L

        private fun todayDateString(): String {
            return SimpleDateFormat("yyyy-MM-dd", Locale.US).format(Date())
        }

        fun getHourlySteps(context: Context): Long {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            val storedHour = prefs.getInt(KEY_CURRENT_HOUR, -1)
            val actualHour = Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
            if (storedHour != -1 && storedHour != actualHour) {
                return 0
            }
            val currentSteps = prefs.getLong(KEY_CURRENT_STEPS, 0)
            val hourStartSteps = prefs.getLong(KEY_HOUR_START_STEPS, 0)
            return kotlin.math.max(0, currentSteps - hourStartSteps)
        }

        fun getStepOffset(context: Context): Int {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            return prefs.getInt(KEY_STEP_OFFSET, DEFAULT_STEP_OFFSET)
        }

        /**
         * Sets the hourly step count to start from this value.
         * Adjusts hour_start_steps so getHourlySteps() returns this value + sensor steps.
         * Resets automatically when the hour changes.
         */
        fun setStartingSteps(context: Context, startingSteps: Int) {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            val currentSteps = prefs.getLong(KEY_CURRENT_STEPS, 0)
            // Set hour_start_steps so that currentSteps - hourStartSteps = startingSteps
            val newHourStart = currentSteps - startingSteps
            prefs.edit()
                .putLong(KEY_HOUR_START_STEPS, newHourStart)
                .putInt(KEY_STEP_OFFSET, startingSteps)
                .apply()
        }

        fun getStepGoal(context: Context): Int {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            return prefs.getInt(KEY_STEP_GOAL, DEFAULT_STEP_GOAL)
        }

        fun setStepGoal(context: Context, goal: Int) {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            prefs.edit().putInt(KEY_STEP_GOAL, goal).apply()
        }

        fun isAlarmEnabled(context: Context): Boolean {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            return prefs.getBoolean(KEY_ALARM_ENABLED, true)
        }

        fun setAlarmEnabled(context: Context, enabled: Boolean) {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            prefs.edit().putBoolean(KEY_ALARM_ENABLED, enabled).apply()
        }

        fun getAlarmDuration(context: Context): Int {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            return prefs.getInt(KEY_ALARM_DURATION, DEFAULT_ALARM_DURATION)
        }

        fun setAlarmDuration(context: Context, seconds: Int) {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            prefs.edit().putInt(KEY_ALARM_DURATION, seconds).apply()
        }

        fun getIntervalStart(context: Context): Int {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            return prefs.getInt(KEY_INTERVAL_START, DEFAULT_INTERVAL_START)
        }

        fun setIntervalStart(context: Context, hour: Int) {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            prefs.edit().putInt(KEY_INTERVAL_START, hour).apply()
        }

        fun getIntervalEnd(context: Context): Int {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            return prefs.getInt(KEY_INTERVAL_END, DEFAULT_INTERVAL_END)
        }

        fun setIntervalEnd(context: Context, hour: Int) {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            prefs.edit().putInt(KEY_INTERVAL_END, hour).apply()
        }

        /**
         * Returns completed/elapsed as a Pair (e.g. Pair(3, 5) means 3 out of 5 hours goal met).
         * Only counts hours within the configured interval.
         * Current hour is included if goal is reached.
         */
        fun getHourlyProgress(context: Context): Pair<Int, Int> {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            val intervalStart = prefs.getInt(KEY_INTERVAL_START, DEFAULT_INTERVAL_START)
            val intervalEnd = prefs.getInt(KEY_INTERVAL_END, DEFAULT_INTERVAL_END)
            val currentHour = Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
            val stepGoal = prefs.getInt(KEY_STEP_GOAL, DEFAULT_STEP_GOAL)

            // If outside interval, return 0/0
            if (currentHour < intervalStart || currentHour >= intervalEnd) {
                return Pair(0, 0)
            }

            // Load completed hours for today
            val today = todayDateString()
            val storedDate = prefs.getString(KEY_COMPLETED_HOURS_DATE, "") ?: ""
            val completedSet = if (storedDate == today) {
                prefs.getStringSet(KEY_COMPLETED_HOURS, emptySet()) ?: emptySet()
            } else {
                emptySet()
            }

            // Elapsed hours = from intervalStart to currentHour (inclusive)
            val elapsed = currentHour - intervalStart + 1

            // Completed = past hours in set + current hour if goal reached
            var completed = completedSet.count { hourStr ->
                val h = hourStr.toIntOrNull() ?: -1
                h in intervalStart until currentHour
            }

            // Check current hour
            val hourlySteps = getHourlySteps(context)
            if (hourlySteps >= stepGoal) {
                completed++
            }

            return Pair(completed, elapsed)
        }

        /**
         * Record that a given hour had its goal completed. Called on hour change.
         */
        fun recordCompletedHour(context: Context, hour: Int) {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            val today = todayDateString()
            val storedDate = prefs.getString(KEY_COMPLETED_HOURS_DATE, "") ?: ""

            val currentSet = if (storedDate == today) {
                (prefs.getStringSet(KEY_COMPLETED_HOURS, emptySet()) ?: emptySet()).toMutableSet()
            } else {
                mutableSetOf()
            }

            currentSet.add(hour.toString())
            prefs.edit()
                .putString(KEY_COMPLETED_HOURS_DATE, today)
                .putStringSet(KEY_COMPLETED_HOURS, currentSet)
                .apply()

            Log.e(TAG, "Recorded completed hour $hour, total today: $currentSet")
        }
    }

    private lateinit var sensorManager: SensorManager
    private var stepCounterSensor: Sensor? = null
    private lateinit var prefs: SharedPreferences
    private var currentHour: Int = -1
    private val handler = Handler(Looper.getMainLooper())
    private var vibrator: Vibrator? = null
    private var isVibrating = false
    private var isScreenOn = true

    private val alarmCheckRunnable = object : Runnable {
        override fun run() {
            checkAndTriggerAlarm()
            handler.postDelayed(this, ALARM_CHECK_INTERVAL_MS)
        }
    }

    private val screenOnUpdateRunnable = object : Runnable {
        override fun run() {
            if (isScreenOn) {
                try {
                    requestComplicationUpdate()
                } catch (e: Exception) {
                    Log.e(TAG, "Error in screen update runnable", e)
                }
                handler.postDelayed(this, SCREEN_ON_UPDATE_INTERVAL_MS)
            }
        }
    }

    private val screenReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            when (intent.action) {
                Intent.ACTION_SCREEN_ON -> {
                    Log.e(TAG, "Screen ON — starting fast complication updates")
                    isScreenOn = true
                    handler.removeCallbacks(screenOnUpdateRunnable)
                    handler.post(screenOnUpdateRunnable)
                }
                Intent.ACTION_SCREEN_OFF -> {
                    Log.e(TAG, "Screen OFF — stopping fast complication updates")
                    isScreenOn = false
                    handler.removeCallbacks(screenOnUpdateRunnable)
                }
            }
        }
    }

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

        vibrator = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
            val vm = getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager
            vm.defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
        }

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

        val filter = IntentFilter().apply {
            addAction(Intent.ACTION_SCREEN_ON)
            addAction(Intent.ACTION_SCREEN_OFF)
        }
        registerReceiver(screenReceiver, filter, Context.RECEIVER_NOT_EXPORTED)

        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        isScreenOn = powerManager.isInteractive
        Log.e(TAG, "Initial screen state: isScreenOn=$isScreenOn")
        if (isScreenOn) {
            handler.post(screenOnUpdateRunnable)
        }

        // Start alarm check every 30s (backup for AlarmManager)
        handler.postDelayed(alarmCheckRunnable, ALARM_CHECK_INTERVAL_MS)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_VIBRATE_ALARM) {
            triggerVibration()
        }
        return START_STICKY
    }

    private fun checkAndTriggerAlarm() {
        val calendar = Calendar.getInstance()
        val minute = calendar.get(Calendar.MINUTE)
        val hour = calendar.get(Calendar.HOUR_OF_DAY)

        if (!prefs.getBoolean(KEY_ALARM_ENABLED, true)) return
        if (minute < ALARM_TRIGGER_MINUTE) return
        if (isVibrating) return

        val intervalStart = prefs.getInt(KEY_INTERVAL_START, DEFAULT_INTERVAL_START)
        val intervalEnd = prefs.getInt(KEY_INTERVAL_END, DEFAULT_INTERVAL_END)
        if (hour < intervalStart || hour >= intervalEnd) return

        val dismissedHour = prefs.getInt(KEY_ALARM_DISMISSED_HOUR, -1)
        if (dismissedHour == hour) return

        val hourlySteps = getHourlySteps(this)
        val stepGoal = prefs.getInt(KEY_STEP_GOAL, DEFAULT_STEP_GOAL)

        if (hourlySteps < stepGoal) {
            Log.e(TAG, "Handler alarm triggered! minute=$minute, steps=$hourlySteps, goal=$stepGoal")
            prefs.edit().putInt(KEY_ALARM_DISMISSED_HOUR, hour).apply()
            triggerVibration()
        }
    }

    private fun triggerVibration() {
        isVibrating = true
        val duration = prefs.getInt(KEY_ALARM_DURATION, DEFAULT_ALARM_DURATION)
        Log.e(TAG, "Vibrating for ${duration}s from foreground service")

        // Repeating pattern: 800ms strong buzz, 400ms pause — much more noticeable
        val pattern = longArrayOf(0, 800, 400)
        vibrator?.vibrate(VibrationEffect.createWaveform(pattern, 0)) // 0 = repeat from index 0

        // Stop after configured duration
        handler.postDelayed({
            vibrator?.cancel()
            isVibrating = false
            Log.e(TAG, "Vibration stopped after ${duration}s")
        }, duration * 1000L)
    }

    override fun onSensorChanged(event: SensorEvent?) {
        event?.let {
            if (it.sensor.type == Sensor.TYPE_STEP_COUNTER) {
                val totalSteps = it.values[0].toLong()
                updateStepCount(totalSteps)
            }
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}

    private fun updateStepCount(totalSteps: Long) {
        val calendar = Calendar.getInstance()
        val hour = calendar.get(Calendar.HOUR_OF_DAY)

        if (hour != currentHour) {
            Log.e(TAG, "New hour detected: $hour (previous: $currentHour)")

            // Calculate previous hour steps directly from prefs (before reset)
            // Can't use getHourlySteps() here because it returns 0 when hour changed
            val prevCurrentSteps = prefs.getLong(KEY_CURRENT_STEPS, 0)
            val prevHourStartSteps = prefs.getLong(KEY_HOUR_START_STEPS, 0)
            val previousHourSteps = kotlin.math.max(0, prevCurrentSteps - prevHourStartSteps)
            val stepGoal = prefs.getInt(KEY_STEP_GOAL, DEFAULT_STEP_GOAL)
            Log.e(TAG, "Previous hour steps: $previousHourSteps, goal: $stepGoal")
            if (previousHourSteps >= stepGoal) {
                recordCompletedHour(this, currentHour)
            }

            prefs.edit()
                .putLong(KEY_HOUR_START_STEPS, totalSteps)
                .putLong(KEY_HOUR_START_TIME, calendar.timeInMillis)
                .putInt(KEY_CURRENT_HOUR, hour)
                .putInt(KEY_STEP_OFFSET, 0)
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

    private fun requestComplicationUpdate() {
        try {
            Log.e(TAG, "Requesting complication update")
            val componentName = ComponentName(this, HourlyStepsComplicationService::class.java)
            ComplicationDataSourceUpdateRequester
                .create(context = this, complicationDataSourceComponent = componentName)
                .requestUpdateAll()
        } catch (e: Exception) {
            Log.e(TAG, "Failed to update complications", e)
        }
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
        handler.removeCallbacks(alarmCheckRunnable)
        handler.removeCallbacks(screenOnUpdateRunnable)
        vibrator?.cancel()
        unregisterReceiver(screenReceiver)
        sensorManager.unregisterListener(this)
        Log.e(TAG, "Service destroyed")
    }

    override fun onBind(intent: Intent?): IBinder? {
        return null
    }
}
