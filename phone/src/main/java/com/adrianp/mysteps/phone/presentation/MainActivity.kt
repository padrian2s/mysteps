package com.adrianp.mysteps.phone.presentation

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import com.adrianp.mysteps.phone.service.PhoneStepService
import kotlinx.coroutines.delay
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : ComponentActivity() {

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { results ->
        if (results.values.any { it }) {
            startStepService()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        if (hasRequiredPermissions()) {
            startStepService()
        }
        requestPermissions()

        setContent {
            MaterialTheme {
                StepDashboard()
            }
        }
    }

    private fun hasRequiredPermissions(): Boolean {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            return ContextCompat.checkSelfPermission(
                this, Manifest.permission.POST_NOTIFICATIONS
            ) == PackageManager.PERMISSION_GRANTED
        }
        return true
    }

    private fun requestPermissions() {
        val perms = mutableListOf<String>()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            perms.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        val needed = perms.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (needed.isNotEmpty()) {
            permissionLauncher.launch(needed.toTypedArray())
        }
    }

    private fun startStepService() {
        if (!hasRequiredPermissions()) return
        try {
            startForegroundService(Intent(this, PhoneStepService::class.java))
        } catch (_: Exception) {}
    }
}

@Composable
fun StepDashboard() {
    val context = LocalContext.current

    var hourlySteps by remember { mutableLongStateOf(0L) }
    var stepGoal by remember { mutableIntStateOf(PhoneStepService.DEFAULT_STEP_GOAL) }
    var completedHours by remember { mutableIntStateOf(0) }
    var elapsedHours by remember { mutableIntStateOf(0) }
    var lastSync by remember { mutableLongStateOf(0L) }
    var alarmEnabled by remember { mutableStateOf(PhoneStepService.isAlarmEnabled(context)) }
    var refreshTick by remember { mutableLongStateOf(0L) }

    LaunchedEffect(refreshTick) {
        while (true) {
            hourlySteps = PhoneStepService.getHourlySteps(context)
            stepGoal = PhoneStepService.getStepGoal(context)
            completedHours = PhoneStepService.getCompletedHours(context)
            elapsedHours = PhoneStepService.getElapsedHours(context)
            lastSync = PhoneStepService.getLastSync(context)
            delay(2000)
        }
    }

    val progress = if (stepGoal > 0) (hourlySteps.toFloat() / stepGoal).coerceIn(0f, 1f) else 0f
    val goalReached = hourlySteps >= stepGoal
    val syncText = if (lastSync > 0) {
        "Last sync: ${SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date(lastSync))}"
    } else {
        "Waiting for watch data..."
    }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(modifier = Modifier.height(48.dp))

            Text(
                text = if (goalReached) "✓" else "$hourlySteps",
                fontSize = 72.sp,
                fontWeight = FontWeight.Bold,
                color = if (goalReached) MaterialTheme.colorScheme.primary
                        else MaterialTheme.colorScheme.onBackground
            )
            Text(
                text = "steps this hour",
                fontSize = 18.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            if (elapsedHours > 0) {
                Text(
                    text = "$completedHours / $elapsedHours hours completed",
                    fontSize = 16.sp,
                    color = MaterialTheme.colorScheme.primary
                )
            }

            Spacer(modifier = Modifier.height(4.dp))

            Text(
                text = "Goal: $stepGoal steps/hour",
                fontSize = 14.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(modifier = Modifier.height(12.dp))

            LinearProgressIndicator(
                progress = { progress },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(8.dp),
            )

            Spacer(modifier = Modifier.height(16.dp))

            TextButton(onClick = { refreshTick++ }) {
                Text("↻ Refresh", fontSize = 16.sp)
            }

            Text(
                text = syncText,
                fontSize = 12.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(modifier = Modifier.height(8.dp))

            OutlinedButton(onClick = {
                val intent = Intent(context, PhoneStepService::class.java).apply {
                    action = PhoneStepService.ACTION_TEST
                }
                context.startForegroundService(intent)
            }) {
                Text("Test Notification")
            }

            Spacer(modifier = Modifier.weight(1f))

            // Notification toggle
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text("Phone Notifications", style = MaterialTheme.typography.bodyLarge)
                    Text(
                        "Alert when steps not reached",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Switch(
                    checked = alarmEnabled,
                    onCheckedChange = {
                        alarmEnabled = it
                        PhoneStepService.setAlarmEnabled(context, it)
                    }
                )
            }

            Spacer(modifier = Modifier.height(16.dp))
        }
    }
}
