package com.adrianp.mysteps.presentation

import android.Manifest
import android.content.ComponentName
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.wear.compose.foundation.lazy.AutoCenteringParams
import androidx.wear.compose.foundation.lazy.ScalingLazyColumn
import androidx.wear.compose.foundation.lazy.rememberScalingLazyListState
import androidx.wear.compose.material.Button
import androidx.wear.compose.material.ButtonDefaults
import androidx.wear.compose.material.ChipDefaults
import androidx.wear.compose.material.CompactChip
import androidx.wear.compose.material.MaterialTheme
import androidx.wear.compose.material.PositionIndicator
import androidx.wear.compose.material.Scaffold
import androidx.wear.compose.material.Switch
import androidx.wear.compose.material.Text
import androidx.wear.compose.material.TimeText
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceUpdateRequester
import com.adrianp.mysteps.complication.HourlyStepsComplicationService
import com.adrianp.mysteps.presentation.theme.MyStepsTheme
import com.adrianp.mysteps.service.HourStatus
import com.adrianp.mysteps.service.StepCounterService

private val PanelColor = Color(0xFF202124)
private val HeartColor = Color(0xFFFF6B6B)
private val LabelColor = Color.White.copy(alpha = 0.7f)
private val HintColor = Color.White.copy(alpha = 0.5f)
private const val MAX_HOUR_DOTS_PER_ROW = 13

class MainActivity : ComponentActivity() {

    // Both permissions in one request: a second request launched while the first
    // dialog is showing gets cancelled by the system
    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { results ->
        if (results[Manifest.permission.ACTIVITY_RECOGNITION] == true) {
            startStepCounterService()
        }
    }

    // Live values, re-read on resume and after every change that affects them
    private var stepsThisHour by mutableLongStateOf(0L)
    private var todayHours by mutableStateOf(emptyList<HourStatus>())
    // Rollover resets it to 0, so it's re-read with the rest instead of kept in UI state
    private var stepOffset by mutableIntStateOf(0)

    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()

        super.onCreate(savedInstanceState)

        setTheme(android.R.style.Theme_DeviceDefault)

        val missingPermissions = mutableListOf<String>()
        if (hasActivityRecognitionPermission()) {
            startStepCounterService()
        } else {
            missingPermissions.add(Manifest.permission.ACTIVITY_RECOGNITION)
        }

        // Request notification permission (SDK 33+)
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED) {
                missingPermissions.add(Manifest.permission.POST_NOTIFICATIONS)
            }
        }
        if (missingPermissions.isNotEmpty()) {
            permissionLauncher.launch(missingPermissions.toTypedArray())
        }

        // Ensure alarm is always scheduled
        com.adrianp.mysteps.service.StepAlarmReceiver.scheduleAllAlarms(this)

        refreshProgress()

        val currentGoal = StepCounterService.getStepGoal(this)
        val alarmOn = StepCounterService.isAlarmEnabled(this)
        val intervalStart = StepCounterService.getIntervalStart(this)
        val intervalEnd = StepCounterService.getIntervalEnd(this)
        val alarmDuration = StepCounterService.getAlarmDuration(this)

        setContent {
            SettingsScreen(
                stepsThisHour = stepsThisHour,
                todayHours = todayHours,
                initialGoal = currentGoal,
                stepOffset = stepOffset,
                initialAlarmEnabled = alarmOn,
                initialAlarmDuration = alarmDuration,
                initialIntervalStart = intervalStart,
                initialIntervalEnd = intervalEnd,
                onGoalChanged = {
                    StepCounterService.setStepGoal(this, it)
                    refreshProgress()
                },
                onStepOffsetChanged = {
                    StepCounterService.setStartingSteps(this, it)
                    refreshProgress()
                },
                onAlarmToggled = { StepCounterService.setAlarmEnabled(this, it) },
                onAlarmDurationChanged = { StepCounterService.setAlarmDuration(this, it) },
                onIntervalStartChanged = {
                    StepCounterService.setIntervalStart(this, it)
                    refreshProgress()
                },
                onIntervalEndChanged = {
                    StepCounterService.setIntervalEnd(this, it)
                    refreshProgress()
                },
                onAddSteps = {
                    StepCounterService.addSyntheticSteps(this, it)
                    refreshProgress()
                    requestComplicationUpdate()
                }
            )
        }
    }

    override fun onResume() {
        super.onResume()
        refreshProgress()
    }

    override fun onStop() {
        super.onStop()
        // Show changed settings (goal, Fitbit Sync) on the watch face right away
        requestComplicationUpdate()
    }

    private fun refreshProgress() {
        // Start this hour's window if no step arrived yet, so nothing shown is from last hour
        StepCounterService.rolloverIfNeeded(this)
        stepsThisHour = StepCounterService.getHourlySteps(this)
        todayHours = StepCounterService.getTodayHours(this)
        stepOffset = StepCounterService.getStepOffset(this)
    }

    private fun hasActivityRecognitionPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.ACTIVITY_RECOGNITION
        ) == PackageManager.PERMISSION_GRANTED
    }

    private fun requestComplicationUpdate() {
        try {
            val componentName = ComponentName(this, HourlyStepsComplicationService::class.java)
            ComplicationDataSourceUpdateRequester
                .create(context = this, complicationDataSourceComponent = componentName)
                .requestUpdateAll()
        } catch (e: Exception) {
            Log.e("MainActivity", "Failed to update complications", e)
        }
    }

    private fun startStepCounterService() {
        try {
            Log.e("MainActivity", "Starting StepCounterService...")
            val serviceIntent = Intent(this, StepCounterService::class.java)
            startForegroundService(serviceIntent)
            Log.e("MainActivity", "StepCounterService started successfully")
        } catch (e: Exception) {
            Log.e("MainActivity", "Failed to start StepCounterService", e)
        }
    }

}

private fun formatHour(hour: Int): String {
    return if (hour < 10) "0$hour:00" else "$hour:00"
}

/** Rounded card that groups one setting. */
@Composable
private fun Panel(
    title: String? = null,
    subtitle: String? = null,
    content: @Composable ColumnScope.() -> Unit
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 4.dp)
            .clip(RoundedCornerShape(20.dp))
            .background(PanelColor)
            .padding(horizontal = 10.dp, vertical = 10.dp)
    ) {
        if (title != null) {
            Text(text = title, fontSize = 12.sp, color = LabelColor)
        }
        if (subtitle != null) {
            Text(text = subtitle, fontSize = 9.sp, color = HintColor)
        }
        if (title != null || subtitle != null) {
            Spacer(modifier = Modifier.height(6.dp))
        }
        content()
    }
}

@Composable
private fun ValueStepper(
    value: String,
    onDecrement: () -> Unit,
    onIncrement: () -> Unit,
    decrementEnabled: Boolean = true,
    incrementEnabled: Boolean = true,
    valueColor: Color = MaterialTheme.colors.primary
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center
    ) {
        StepperButton(symbol = "−", onClick = onDecrement, enabled = decrementEnabled)
        Text(
            text = value,
            fontSize = 18.sp,
            color = valueColor,
            textAlign = TextAlign.Center,
            modifier = Modifier
                .widthIn(min = 60.dp)
                .padding(horizontal = 6.dp)
        )
        StepperButton(symbol = "+", onClick = onIncrement, enabled = incrementEnabled)
    }
}

@Composable
private fun StepperButton(symbol: String, onClick: () -> Unit, enabled: Boolean) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier.size(32.dp),
        colors = ButtonDefaults.secondaryButtonColors()
    ) {
        Text(symbol, fontSize = 16.sp)
    }
}

@Composable
fun HourPicker(
    label: String,
    hour: Int,
    range: IntRange,
    onChanged: (Int) -> Unit
) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(text = label, fontSize = 10.sp, color = HintColor)
        ValueStepper(
            value = formatHour(hour),
            onDecrement = { if (hour > range.first) onChanged(hour - 1) },
            onIncrement = { if (hour < range.last) onChanged(hour + 1) },
            decrementEnabled = hour > range.first,
            incrementEnabled = hour < range.last
        )
    }
}

@Composable
private fun ThisHourPanel(steps: Long, goal: Int, onAddSteps: (Int) -> Unit) {
    Panel {
        if (steps >= goal) {
            Text(text = "❤ $steps", fontSize = 26.sp, color = HeartColor)
            Text(text = "goal reached this hour", fontSize = 11.sp, color = HintColor)
        } else {
            Row {
                Text(
                    text = "$steps",
                    fontSize = 26.sp,
                    color = MaterialTheme.colors.primary,
                    modifier = Modifier.alignByBaseline()
                )
                Text(
                    text = " / $goal",
                    fontSize = 14.sp,
                    color = HintColor,
                    modifier = Modifier.alignByBaseline()
                )
            }
            Text(text = "steps this hour", fontSize = 11.sp, color = HintColor)
            Spacer(modifier = Modifier.height(6.dp))
            Box(
                modifier = Modifier
                    .fillMaxWidth(0.8f)
                    .height(4.dp)
                    .clip(RoundedCornerShape(2.dp))
                    .background(Color.White.copy(alpha = 0.15f))
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth((steps.toFloat() / goal).coerceIn(0f, 1f))
                        .fillMaxHeight()
                        .background(MaterialTheme.colors.primary)
                )
            }
        }
        Spacer(modifier = Modifier.height(8.dp))
        CompactChip(
            onClick = { onAddSteps(300) },
            label = { Text("+300 steps", fontSize = 12.sp) },
            colors = ChipDefaults.secondaryChipColors()
        )
    }
}

@Composable
private fun TodayPanel(hours: List<HourStatus>, intervalStart: Int) {
    val completed = hours.count { it == HourStatus.COMPLETED }
    val counted = completed + hours.count { it == HourStatus.MISSED }
    Panel(title = "Today") {
        when {
            hours.all { it == HourStatus.UPCOMING } ->
                Text(text = "Starts at ${formatHour(intervalStart)}", fontSize = 14.sp, color = LabelColor)
            counted == 0 ->
                Text(text = "First hour in progress", fontSize = 14.sp, color = LabelColor)
            else -> {
                Text(
                    text = "$completed of $counted hours",
                    fontSize = 16.sp,
                    color = MaterialTheme.colors.primary
                )
                Text(text = "goal met", fontSize = 10.sp, color = HintColor)
            }
        }
        if (hours.isNotEmpty()) {
            Spacer(modifier = Modifier.height(8.dp))
            HourDots(hours)
        }
    }
}

/** One dot per hour of the interval: filled = goal met, gray = missed, ring = now, faint = later. */
@Composable
private fun HourDots(hours: List<HourStatus>) {
    val rows = (hours.size + MAX_HOUR_DOTS_PER_ROW - 1) / MAX_HOUR_DOTS_PER_ROW
    val perRow = (hours.size + rows - 1) / rows
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        hours.chunked(perRow).forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                row.forEach { status ->
                    val dot = Modifier
                        .size(7.dp)
                        .clip(CircleShape)
                    Box(
                        modifier = when (status) {
                            HourStatus.COMPLETED -> dot.background(HeartColor)
                            HourStatus.MISSED -> dot.background(Color.White.copy(alpha = 0.35f))
                            HourStatus.IN_PROGRESS -> dot.border(1.5.dp, MaterialTheme.colors.primary, CircleShape)
                            HourStatus.UPCOMING -> dot.background(Color.White.copy(alpha = 0.12f))
                        }
                    )
                }
            }
        }
    }
}

@Composable
fun SettingsScreen(
    stepsThisHour: Long,
    todayHours: List<HourStatus>,
    initialGoal: Int,
    stepOffset: Int,
    initialAlarmEnabled: Boolean,
    initialAlarmDuration: Int,
    initialIntervalStart: Int,
    initialIntervalEnd: Int,
    onGoalChanged: (Int) -> Unit,
    onStepOffsetChanged: (Int) -> Unit,
    onAlarmToggled: (Boolean) -> Unit,
    onAlarmDurationChanged: (Int) -> Unit,
    onIntervalStartChanged: (Int) -> Unit,
    onIntervalEndChanged: (Int) -> Unit,
    onAddSteps: (Int) -> Unit
) {
    var stepGoal by remember { mutableIntStateOf(initialGoal) }
    var alarmEnabled by remember { mutableStateOf(initialAlarmEnabled) }
    var alarmDuration by remember { mutableIntStateOf(initialAlarmDuration) }
    var intervalStart by remember { mutableIntStateOf(initialIntervalStart) }
    var intervalEnd by remember { mutableIntStateOf(initialIntervalEnd) }
    // Start centered on the first panel so it isn't hidden under the time
    val listState = rememberScalingLazyListState(initialCenterItemIndex = 0)

    MyStepsTheme {
        Scaffold(
            timeText = { TimeText() },
            positionIndicator = { PositionIndicator(scalingLazyListState = listState) }
        ) {
            ScalingLazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .background(MaterialTheme.colors.background),
                state = listState,
                autoCentering = AutoCenteringParams(itemIndex = 0),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                // Steps this hour + synthetic steps (count toward this hour's goal)
                item {
                    ThisHourPanel(steps = stepsThisHour, goal = stepGoal, onAddSteps = onAddSteps)
                }

                // Hours with the goal met today
                item {
                    TodayPanel(hours = todayHours, intervalStart = intervalStart)
                }

                // Step goal setting
                item {
                    Panel(title = "Step Goal") {
                        ValueStepper(
                            value = "$stepGoal",
                            onDecrement = {
                                if (stepGoal > 50) {
                                    stepGoal -= 50
                                    onGoalChanged(stepGoal)
                                }
                            },
                            onIncrement = {
                                stepGoal += 50
                                onGoalChanged(stepGoal)
                            },
                            decrementEnabled = stepGoal > 50
                        )
                    }
                }

                // Fitbit Sync offset
                item {
                    Panel(title = "Fitbit Sync", subtitle = "Starting steps per hour") {
                        ValueStepper(
                            value = "$stepOffset",
                            onDecrement = { if (stepOffset > 0) onStepOffsetChanged(stepOffset - 1) },
                            onIncrement = { onStepOffsetChanged(stepOffset + 1) },
                            decrementEnabled = stepOffset > 0,
                            valueColor = if (stepOffset > 0) Color(0xFF4CAF50) else MaterialTheme.colors.primary
                        )
                    }
                }

                // Alarm toggle + duration
                item {
                    Panel {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier
                                .fillMaxWidth()
                                .toggleable(
                                    value = alarmEnabled,
                                    role = Role.Switch,
                                    onValueChange = {
                                        alarmEnabled = it
                                        onAlarmToggled(it)
                                    }
                                )
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(text = "Vibration Alarm", fontSize = 13.sp)
                                Text(text = "10 min before hour", fontSize = 10.sp, color = HintColor)
                            }
                            Switch(checked = alarmEnabled)
                        }
                        if (alarmEnabled) {
                            Spacer(modifier = Modifier.height(8.dp))
                            Text(text = "Duration", fontSize = 10.sp, color = HintColor)
                            ValueStepper(
                                value = "${alarmDuration}s",
                                onDecrement = {
                                    if (alarmDuration > 5) {
                                        alarmDuration -= 5
                                        onAlarmDurationChanged(alarmDuration)
                                    }
                                },
                                onIncrement = {
                                    alarmDuration += 5
                                    onAlarmDurationChanged(alarmDuration)
                                },
                                decrementEnabled = alarmDuration > 5
                            )
                        }
                    }
                }

                // Active interval
                item {
                    Panel(title = "Active Hours") {
                        HourPicker(
                            label = "Start",
                            hour = intervalStart,
                            range = 0 until intervalEnd,
                            onChanged = {
                                intervalStart = it
                                onIntervalStartChanged(it)
                            }
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        HourPicker(
                            label = "End",
                            hour = intervalEnd,
                            range = (intervalStart + 1)..23,
                            onChanged = {
                                intervalEnd = it
                                onIntervalEndChanged(it)
                            }
                        )
                    }
                }
            }
        }
    }
}
