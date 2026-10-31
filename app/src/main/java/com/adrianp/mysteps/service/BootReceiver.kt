package com.adrianp.mysteps.service

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.util.Log
import androidx.core.content.ContextCompat

/**
 * Restarts tracking after a reboot or an app update. These broadcasts are among the few
 * places a background app may start a foreground service; the complication can't.
 */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED &&
            intent.action != Intent.ACTION_MY_PACKAGE_REPLACED
        ) return

        Log.e("BootReceiver", "${intent.action} — scheduling step alarm and starting service")
        StepAlarmReceiver.scheduleAllAlarms(context)

        // Health-type foreground service: needs ACTIVITY_RECOGNITION or startForeground throws
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.ACTIVITY_RECOGNITION)
            != PackageManager.PERMISSION_GRANTED
        ) return
        try {
            context.startForegroundService(Intent(context, StepCounterService::class.java))
        } catch (e: Exception) {
            Log.e("BootReceiver", "Failed to start StepCounterService", e)
        }
    }
}
