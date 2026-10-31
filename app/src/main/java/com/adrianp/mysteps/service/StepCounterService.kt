package com.adrianp.mysteps.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.ComponentName
import android.content.pm.ServiceInfo
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorEventListener2
import android.hardware.SensorManager
import android.hardware.display.DisplayManager
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.SystemClock
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.util.Log
import android.view.Display
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceUpdateRequester
import com.adrianp.mysteps.complication.HourlyStepsComplicationService
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale

enum class HourStatus { COMPLETED, MISSED, IN_PROGRESS, UPCOMING }

class StepCounterService : Service(), SensorEventListener2 {

    companion object {
        private const val TAG = "StepCounterService"
        private const val NOTIFICATION_ID = 1
        private const val CHANNEL_ID = "step_counter_channel"
        const val PREFS_NAME = "hourly_steps_prefs"
        const val KEY_HOUR_START_STEPS = "hour_start_steps"
        const val KEY_HOUR_START_TIME = "hour_start_time"
        const val KEY_CURRENT_STEPS = "current_steps"
        const val KEY_LAST_UPDATE = "last_update"
        const val KEY_STEP_GOAL = "step_goal"
        const val KEY_ALARM_ENABLED = "alarm_enabled"
        const val KEY_ALARM_DISMISSED_HOUR_START = "alarm_dismissed_hour_start"
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
        // Minimum time between complication refreshes while the screen is on
        private const val SCREEN_ON_UPDATE_INTERVAL_MS = 2_000L
        // Max wait for the sensor to hand over steps batched while the screen was off
        private const val FLUSH_TIMEOUT_MS = 1_000L

        private fun dateString(timeMs: Long = System.currentTimeMillis()): String {
            return SimpleDateFormat("yyyy-MM-dd", Locale.US).format(Date(timeMs))
        }

        /**
         * Start of the clock hour containing [timeMs]. Unlike HOUR_OF_DAY it also
         * identifies the day, so 14:00 today never matches 14:00 yesterday.
         */
        fun hourStartMillis(timeMs: Long = System.currentTimeMillis()): Long {
            return Calendar.getInstance().apply {
                timeInMillis = timeMs
                set(Calendar.MINUTE, 0)
                set(Calendar.SECOND, 0)
                set(Calendar.MILLISECOND, 0)
            }.timeInMillis
        }

        private fun storedHourStart(prefs: SharedPreferences): Long? {
            if (!prefs.contains(KEY_HOUR_START_TIME)) return null
            return hourStartMillis(prefs.getLong(KEY_HOUR_START_TIME, 0))
        }

        fun getHourlySteps(context: Context): Long {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            val storedHourStart = storedHourStart(prefs)
            if (storedHourStart != null && storedHourStart != hourStartMillis()) {
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
            rolloverIfNeeded(context)
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            val currentSteps = prefs.getLong(KEY_CURRENT_STEPS, 0)
            // Set hour_start_steps so that currentSteps - hourStartSteps = startingSteps
            val newHourStart = currentSteps - startingSteps
            prefs.edit()
                .putLong(KEY_HOUR_START_STEPS, newHourStart)
                .putInt(KEY_STEP_OFFSET, startingSteps)
                .apply()
        }

        /**
         * Adds synthetic steps to the current hour. These are "real" within the app:
         * they count toward the hourly goal, show in the complication/tile, and silence
         * the alarm. Done by lowering hour_start_steps so getHourlySteps() returns +amount.
         * Resets automatically when the hour changes, just like real steps.
         */
        fun addSyntheticSteps(context: Context, amount: Int) {
            rolloverIfNeeded(context)
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            val hourStartSteps = prefs.getLong(KEY_HOUR_START_STEPS, 0)
            prefs.edit()
                .putLong(KEY_HOUR_START_STEPS, hourStartSteps - amount)
                .apply()
            val hourlySteps = getHourlySteps(context)
            Log.e(TAG, "Added $amount synthetic steps, new hourly: $hourlySteps")
            if (hourlySteps >= getStepGoal(context)) {
                StepAlarmReceiver.cancelAlarmNotification(context)
            }
        }

        /**
         * Starts a new hourly window when the stored one belongs to an earlier hour (or day).
         * The finished hour is recorded as completed under its own date before the baseline resets.
         * Without [totalSteps] (no fresh sensor reading) the last known total becomes the baseline,
         * so synthetic steps and Fitbit Sync work even before the first step of the hour.
         */
        fun rolloverIfNeeded(context: Context, totalSteps: Long? = null) {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            val storedHourStart = storedHourStart(prefs)
            val nowHourStart = hourStartMillis()
            if (storedHourStart == nowHourStart) return

            val lastTotal = if (prefs.contains(KEY_CURRENT_STEPS)) prefs.getLong(KEY_CURRENT_STEPS, 0) else null
            if (storedHourStart != null && lastTotal != null) {
                val previousHourSteps = kotlin.math.max(0, lastTotal - prefs.getLong(KEY_HOUR_START_STEPS, lastTotal))
                val stepGoal = prefs.getInt(KEY_STEP_GOAL, DEFAULT_STEP_GOAL)
                Log.e(TAG, "New hour detected, previous hour steps: $previousHourSteps, goal: $stepGoal")
                if (previousHourSteps >= stepGoal) {
                    recordCompletedHour(context, storedHourStart)
                }
            }

            val baseline = totalSteps ?: lastTotal
            val editor = prefs.edit()
                .putLong(KEY_HOUR_START_TIME, nowHourStart)
                .putInt(KEY_STEP_OFFSET, 0)
            if (baseline != null) {
                editor.putLong(KEY_HOUR_START_STEPS, baseline)
            } else {
                editor.remove(KEY_HOUR_START_STEPS)
            }
            editor.apply()
            Log.e(TAG, "Hour baseline reset to: $baseline")
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
         * Status of every hour in today's active interval, in order. The current hour counts
         * as completed once its goal is reached; until then it is in progress, not missed.
         */
        fun getTodayHours(context: Context): List<HourStatus> {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            val intervalStart = prefs.getInt(KEY_INTERVAL_START, DEFAULT_INTERVAL_START)
            val intervalEnd = prefs.getInt(KEY_INTERVAL_END, DEFAULT_INTERVAL_END)
            val currentHour = Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
            val stepGoal = prefs.getInt(KEY_STEP_GOAL, DEFAULT_STEP_GOAL)

            // Load completed hours for today
            val today = dateString()
            val storedDate = prefs.getString(KEY_COMPLETED_HOURS_DATE, "") ?: ""
            val completedSet = if (storedDate == today) {
                prefs.getStringSet(KEY_COMPLETED_HOURS, emptySet()) ?: emptySet()
            } else {
                emptySet()
            }
            val currentHourReached = getHourlySteps(context) >= stepGoal

            return (intervalStart until intervalEnd).map { hour ->
                when {
                    hour < currentHour ->
                        if (hour.toString() in completedSet) HourStatus.COMPLETED else HourStatus.MISSED
                    hour == currentHour ->
                        if (currentHourReached) HourStatus.COMPLETED else HourStatus.IN_PROGRESS
                    else -> HourStatus.UPCOMING
                }
            }
        }

        /**
         * Returns completed/counted as a Pair (e.g. Pair(3, 5) means 3 out of 5 hours goal met).
         * Counted = finished hours of the interval, plus the current hour once its goal is reached.
         */
        fun getHourlyProgress(context: Context): Pair<Int, Int> {
            val hours = getTodayHours(context)
            val completed = hours.count { it == HourStatus.COMPLETED }
            return Pair(completed, completed + hours.count { it == HourStatus.MISSED })
        }

        /**
         * Record that the hour starting at [hourStartMs] had its goal completed. Called on hour
         * change, which can happen the next day, so the date comes from the hour itself.
         */
        fun recordCompletedHour(context: Context, hourStartMs: Long) {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            val date = dateString(hourStartMs)
            val hour = Calendar.getInstance().apply { timeInMillis = hourStartMs }.get(Calendar.HOUR_OF_DAY)
            val storedDate = prefs.getString(KEY_COMPLETED_HOURS_DATE, "") ?: ""

            val currentSet = if (storedDate == date) {
                (prefs.getStringSet(KEY_COMPLETED_HOURS, emptySet()) ?: emptySet()).toMutableSet()
            } else {
                mutableSetOf()
            }

            currentSet.add(hour.toString())
            prefs.edit()
                .putString(KEY_COMPLETED_HOURS_DATE, date)
                .putStringSet(KEY_COMPLETED_HOURS, currentSet)
                .apply()

            Log.e(TAG, "Recorded completed hour $hour on $date, total: $currentSet")
        }
    }

    private lateinit var sensorManager: SensorManager
    private var stepCounterSensor: Sensor? = null
    private lateinit var prefs: SharedPreferences
    private val handler = Handler(Looper.getMainLooper())
    private var vibrator: Vibrator? = null
    private var isVibrating = false
    private var isScreenOn = true
    private var lastComplicationUpdateMs = 0L

    private val alarmCheckRunnable = object : Runnable {
        override fun run() {
            checkAndTriggerAlarm()
            handler.postDelayed(this, ALARM_CHECK_INTERVAL_MS)
        }
    }

    private val complicationUpdateRunnable = Runnable { requestComplicationUpdate() }

    private var flushPending = false
    private val flushTimeoutRunnable = Runnable { finishScreenOnRefresh() }

    private lateinit var displayManager: DisplayManager

    /**
     * Follows the display itself rather than ACTION_SCREEN_ON/OFF: raising the wrist (TILT)
     * turns the display ON while the device stays non-interactive ("Dozing"), so those
     * broadcasts only arrive after a button press or a touch.
     */
    private val displayListener = object : DisplayManager.DisplayListener {
        override fun onDisplayChanged(displayId: Int) {
            if (displayId != Display.DEFAULT_DISPLAY) return
            val on = isDisplayOn()
            if (on == isScreenOn) return
            isScreenOn = on
            if (on) {
                Log.e(TAG, "Display ON — flushing sensor, then refreshing complication")
                refreshOnScreenOn()
            } else {
                Log.e(TAG, "Display off/ambient — stopping complication updates")
                handler.removeCallbacks(complicationUpdateRunnable)
                handler.removeCallbacks(flushTimeoutRunnable)
                flushPending = false
            }
        }
        override fun onDisplayAdded(displayId: Int) {}
        override fun onDisplayRemoved(displayId: Int) {}
    }

    private fun isDisplayOn(): Boolean =
        displayManager.getDisplay(Display.DEFAULT_DISPLAY)?.state == Display.STATE_ON

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

        displayManager = getSystemService(DisplayManager::class.java)
        displayManager.registerDisplayListener(displayListener, handler)
        isScreenOn = isDisplayOn()
        Log.e(TAG, "Initial screen state: isScreenOn=$isScreenOn")
        scheduleComplicationUpdate()

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
        val hourStart = hourStartMillis(calendar.timeInMillis)

        if (!prefs.getBoolean(KEY_ALARM_ENABLED, true)) return
        if (minute < ALARM_TRIGGER_MINUTE) return
        if (isVibrating) return

        val intervalStart = prefs.getInt(KEY_INTERVAL_START, DEFAULT_INTERVAL_START)
        val intervalEnd = prefs.getInt(KEY_INTERVAL_END, DEFAULT_INTERVAL_END)
        if (hour < intervalStart || hour >= intervalEnd) return

        if (prefs.getLong(KEY_ALARM_DISMISSED_HOUR_START, -1) == hourStart) return

        val hourlySteps = getHourlySteps(this)
        val stepGoal = prefs.getInt(KEY_STEP_GOAL, DEFAULT_STEP_GOAL)

        if (hourlySteps < stepGoal) {
            Log.e(TAG, "Handler alarm triggered! minute=$minute, steps=$hourlySteps, goal=$stepGoal")
            prefs.edit().putLong(KEY_ALARM_DISMISSED_HOUR_START, hourStart).apply()
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

    override fun onFlushCompleted(sensor: Sensor?) {
        // The batched steps were delivered via onSensorChanged just before this callback
        handler.post { if (flushPending) finishScreenOnRefresh() }
    }

    /**
     * While the screen is off the CPU sleeps and the step counter keeps its events in the
     * sensor FIFO; they only arrive some time after wake-up. Flush first so the complication
     * shows the steps taken with the screen off, not the count from before.
     */
    private fun refreshOnScreenOn() {
        handler.removeCallbacks(complicationUpdateRunnable)
        handler.removeCallbacks(flushTimeoutRunnable)
        flushPending = true
        if (stepCounterSensor != null && sensorManager.flush(this)) {
            handler.postDelayed(flushTimeoutRunnable, FLUSH_TIMEOUT_MS)
        } else {
            finishScreenOnRefresh()
        }
    }

    private fun finishScreenOnRefresh() {
        flushPending = false
        handler.removeCallbacks(flushTimeoutRunnable)
        handler.removeCallbacks(complicationUpdateRunnable)
        rolloverIfNeeded(this)
        Log.d(TAG, "Screen-on complication refresh, hourly=${getHourlySteps(this)}")
        requestComplicationUpdate()
    }

    private fun updateStepCount(totalSteps: Long) {
        val lastTotal = prefs.getLong(KEY_CURRENT_STEPS, -1)
        if (lastTotal >= 0 && totalSteps < lastTotal && prefs.contains(KEY_HOUR_START_STEPS)) {
            // The step counter restarts from 0 after a reboot: shift the baseline so the
            // steps already taken this hour are kept
            Log.e(TAG, "Step counter reset detected ($lastTotal -> $totalSteps), rebasing")
            prefs.edit()
                .putLong(KEY_HOUR_START_STEPS, prefs.getLong(KEY_HOUR_START_STEPS, 0) - lastTotal)
                .putLong(KEY_CURRENT_STEPS, 0)
                .apply()
        }

        rolloverIfNeeded(this, totalSteps)

        if (!prefs.contains(KEY_HOUR_START_STEPS)) {
            Log.e(TAG, "First sensor reading - initializing baseline to: $totalSteps")
            prefs.edit()
                .putLong(KEY_HOUR_START_STEPS, totalSteps)
                .putLong(KEY_HOUR_START_TIME, System.currentTimeMillis())
                .apply()
        }

        val stepGoal = prefs.getInt(KEY_STEP_GOAL, DEFAULT_STEP_GOAL)
        val wasBelowGoal = getHourlySteps(this) < stepGoal

        prefs.edit()
            .putLong(KEY_CURRENT_STEPS, totalSteps)
            .putLong(KEY_LAST_UPDATE, System.currentTimeMillis())
            .apply()

        val hourlySteps = getHourlySteps(this)
        Log.d(TAG, "Steps updated - Total: $totalSteps, Hourly: $hourlySteps")

        if (wasBelowGoal && hourlySteps >= stepGoal) {
            StepAlarmReceiver.cancelAlarmNotification(this)
            if (isVibrating) {
                vibrator?.cancel()
                isVibrating = false
            }
        }
        scheduleComplicationUpdate()
    }

    /**
     * Refreshes the complication while the screen is on, at most once per
     * [SCREEN_ON_UPDATE_INTERVAL_MS]. Steps only change on sensor events, so there is
     * nothing to poll for in between.
     */
    private fun scheduleComplicationUpdate() {
        if (!isScreenOn || handler.hasCallbacks(complicationUpdateRunnable)) return
        val sinceLast = SystemClock.elapsedRealtime() - lastComplicationUpdateMs
        handler.postDelayed(
            complicationUpdateRunnable,
            (SCREEN_ON_UPDATE_INTERVAL_MS - sinceLast).coerceAtLeast(0)
        )
    }

    private fun requestComplicationUpdate() {
        lastComplicationUpdateMs = SystemClock.elapsedRealtime()
        try {
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
        handler.removeCallbacks(complicationUpdateRunnable)
        handler.removeCallbacks(flushTimeoutRunnable)
        vibrator?.cancel()
        displayManager.unregisterDisplayListener(displayListener)
        sensorManager.unregisterListener(this)
        Log.e(TAG, "Service destroyed")
    }

    override fun onBind(intent: Intent?): IBinder? {
        return null
    }
}
