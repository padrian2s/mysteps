package com.example.mysteps.presentation

import android.Manifest
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
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.wear.compose.foundation.lazy.ScalingLazyColumn
import androidx.wear.compose.foundation.lazy.rememberScalingLazyListState
import androidx.wear.compose.material.Button
import androidx.wear.compose.material.ButtonDefaults
import androidx.wear.compose.material.MaterialTheme
import androidx.wear.compose.material.PositionIndicator
import androidx.wear.compose.material.Scaffold
import androidx.wear.compose.material.Text
import androidx.wear.compose.material.TimeText
import androidx.wear.compose.material.Switch
import androidx.wear.compose.material.ToggleChip
import com.example.mysteps.presentation.theme.MyStepsTheme
import com.example.mysteps.service.StepCounterService

class MainActivity : ComponentActivity() {

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) {
            startStepCounterService()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()

        super.onCreate(savedInstanceState)

        setTheme(android.R.style.Theme_DeviceDefault)

        if (hasActivityRecognitionPermission()) {
            startStepCounterService()
        } else {
            permissionLauncher.launch(Manifest.permission.ACTIVITY_RECOGNITION)
        }

        // Ensure alarm is always scheduled
        com.example.mysteps.service.StepAlarmReceiver.scheduleAllAlarms(this)

        val currentSteps = StepCounterService.getHourlySteps(this)
        val currentGoal = StepCounterService.getStepGoal(this)
        val alarmOn = StepCounterService.isAlarmEnabled(this)
        val intervalStart = StepCounterService.getIntervalStart(this)
        val intervalEnd = StepCounterService.getIntervalEnd(this)
        val (completed, elapsed) = StepCounterService.getHourlyProgress(this)
        val alarmDuration = StepCounterService.getAlarmDuration(this)

        setContent {
            SettingsScreen(
                initialSteps = currentSteps,
                initialGoal = currentGoal,
                initialAlarmEnabled = alarmOn,
                initialAlarmDuration = alarmDuration,
                initialIntervalStart = intervalStart,
                initialIntervalEnd = intervalEnd,
                completedHours = completed,
                elapsedHours = elapsed,
                onGoalChanged = { StepCounterService.setStepGoal(this, it) },
                onAlarmToggled = { StepCounterService.setAlarmEnabled(this, it) },
                onAlarmDurationChanged = { StepCounterService.setAlarmDuration(this, it) },
                onIntervalStartChanged = { StepCounterService.setIntervalStart(this, it) },
                onIntervalEndChanged = { StepCounterService.setIntervalEnd(this, it) }
            )
        }
    }

    private fun hasActivityRecognitionPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.ACTIVITY_RECOGNITION
        ) == PackageManager.PERMISSION_GRANTED
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

@Composable
fun HourPicker(
    label: String,
    hour: Int,
    onChanged: (Int) -> Unit
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier.fillMaxWidth()
    ) {
        Text(
            text = label,
            fontSize = 12.sp,
            color = Color.White.copy(alpha = 0.7f)
        )
        Spacer(modifier = Modifier.height(4.dp))
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center
        ) {
            Button(
                onClick = { if (hour > 0) onChanged(hour - 1) },
                modifier = Modifier.size(32.dp),
                colors = ButtonDefaults.secondaryButtonColors()
            ) {
                Text("−", fontSize = 16.sp)
            }
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = formatHour(hour),
                fontSize = 18.sp,
                color = MaterialTheme.colors.primary,
                textAlign = TextAlign.Center
            )
            Spacer(modifier = Modifier.width(8.dp))
            Button(
                onClick = { if (hour < 23) onChanged(hour + 1) },
                modifier = Modifier.size(32.dp),
                colors = ButtonDefaults.secondaryButtonColors()
            ) {
                Text("+", fontSize = 16.sp)
            }
        }
    }
}

@Composable
fun SettingsScreen(
    initialSteps: Long,
    initialGoal: Int,
    initialAlarmEnabled: Boolean,
    initialAlarmDuration: Int,
    initialIntervalStart: Int,
    initialIntervalEnd: Int,
    completedHours: Int,
    elapsedHours: Int,
    onGoalChanged: (Int) -> Unit,
    onAlarmToggled: (Boolean) -> Unit,
    onAlarmDurationChanged: (Int) -> Unit,
    onIntervalStartChanged: (Int) -> Unit,
    onIntervalEndChanged: (Int) -> Unit
) {
    var stepGoal by remember { mutableIntStateOf(initialGoal) }
    var alarmEnabled by remember { mutableStateOf(initialAlarmEnabled) }
    var alarmDuration by remember { mutableIntStateOf(initialAlarmDuration) }
    var intervalStart by remember { mutableIntStateOf(initialIntervalStart) }
    var intervalEnd by remember { mutableIntStateOf(initialIntervalEnd) }
    val listState = rememberScalingLazyListState()

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
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                // Current steps + daily progress
                item {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        modifier = Modifier.padding(top = 8.dp)
                    ) {
                        val goalReached = initialSteps >= stepGoal
                        Text(
                            text = if (goalReached) "❤" else "$initialSteps",
                            fontSize = if (goalReached) 28.sp else 24.sp,
                            color = if (goalReached) Color(0xFFFF6B6B) else MaterialTheme.colors.primary,
                            textAlign = TextAlign.Center
                        )
                        if (elapsedHours > 0) {
                            Text(
                                text = "$completedHours/$elapsedHours hours",
                                fontSize = 13.sp,
                                color = Color.White.copy(alpha = 0.8f)
                            )
                        }
                        Text(
                            text = "steps this hour",
                            fontSize = 11.sp,
                            color = Color.White.copy(alpha = 0.6f)
                        )
                    }
                }

                // Step goal setting
                item {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(
                            text = "Step Goal",
                            fontSize = 13.sp,
                            color = Color.White.copy(alpha = 0.7f)
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.Center
                        ) {
                            Button(
                                onClick = {
                                    if (stepGoal > 50) {
                                        stepGoal -= 50
                                        onGoalChanged(stepGoal)
                                    }
                                },
                                modifier = Modifier.size(36.dp),
                                colors = ButtonDefaults.secondaryButtonColors()
                            ) {
                                Text("−", fontSize = 18.sp)
                            }
                            Spacer(modifier = Modifier.width(12.dp))
                            Text(
                                text = "$stepGoal",
                                fontSize = 20.sp,
                                color = MaterialTheme.colors.primary,
                                textAlign = TextAlign.Center
                            )
                            Spacer(modifier = Modifier.width(12.dp))
                            Button(
                                onClick = {
                                    stepGoal += 50
                                    onGoalChanged(stepGoal)
                                },
                                modifier = Modifier.size(36.dp),
                                colors = ButtonDefaults.secondaryButtonColors()
                            ) {
                                Text("+", fontSize = 18.sp)
                            }
                        }
                    }
                }

                // Alarm toggle
                item {
                    ToggleChip(
                        checked = alarmEnabled,
                        onCheckedChange = {
                            alarmEnabled = it
                            onAlarmToggled(it)
                        },
                        label = {
                            Text(text = "Vibration Alarm", fontSize = 13.sp)
                        },
                        secondaryLabel = {
                            Text(
                                text = "10 min before hour",
                                fontSize = 10.sp,
                                color = Color.White.copy(alpha = 0.5f)
                            )
                        },
                        toggleControl = {
                            Switch(checked = alarmEnabled)
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 8.dp)
                    )
                }

                // Alarm duration
                item {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(
                            text = "Alarm Duration",
                            fontSize = 12.sp,
                            color = Color.White.copy(alpha = 0.7f)
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.Center
                        ) {
                            Button(
                                onClick = {
                                    if (alarmDuration > 5) {
                                        alarmDuration -= 5
                                        onAlarmDurationChanged(alarmDuration)
                                    }
                                },
                                modifier = Modifier.size(32.dp),
                                colors = ButtonDefaults.secondaryButtonColors()
                            ) {
                                Text("−", fontSize = 16.sp)
                            }
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "${alarmDuration}s",
                                fontSize = 18.sp,
                                color = MaterialTheme.colors.primary,
                                textAlign = TextAlign.Center
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Button(
                                onClick = {
                                    alarmDuration += 5
                                    onAlarmDurationChanged(alarmDuration)
                                },
                                modifier = Modifier.size(32.dp),
                                colors = ButtonDefaults.secondaryButtonColors()
                            ) {
                                Text("+", fontSize = 16.sp)
                            }
                        }
                    }
                }

                // Interval start
                item {
                    HourPicker(
                        label = "Start Hour",
                        hour = intervalStart,
                        onChanged = {
                            intervalStart = it
                            onIntervalStartChanged(it)
                        }
                    )
                }

                // Interval end
                item {
                    HourPicker(
                        label = "End Hour",
                        hour = intervalEnd,
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
