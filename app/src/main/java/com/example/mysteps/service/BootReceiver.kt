package com.example.mysteps.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            Log.e("BootReceiver", "Boot completed — scheduling step alarm")
            StepAlarmReceiver.scheduleNextAlarm(context)
        }
    }
}
