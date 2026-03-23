package com.adrianp.mysteps.phone.widget

import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.widget.RemoteViews
import com.adrianp.mysteps.phone.R
import com.adrianp.mysteps.phone.service.PhoneStepService

class StepWidget : AppWidgetProvider() {

    override fun onUpdate(context: Context, appWidgetManager: AppWidgetManager, appWidgetIds: IntArray) {
        for (id in appWidgetIds) {
            updateWidget(context, appWidgetManager, id)
        }
    }

    companion object {
        fun updateAll(context: Context) {
            val manager = AppWidgetManager.getInstance(context)
            val ids = manager.getAppWidgetIds(ComponentName(context, StepWidget::class.java))
            for (id in ids) {
                updateWidget(context, manager, id)
            }
        }

        private fun updateWidget(context: Context, manager: AppWidgetManager, widgetId: Int) {
            val steps = PhoneStepService.getHourlySteps(context)
            val goal = PhoneStepService.getStepGoal(context)
            val completed = PhoneStepService.getCompletedHours(context)
            val elapsed = PhoneStepService.getElapsedHours(context)
            val goalReached = steps >= goal

            val views = RemoteViews(context.packageName, R.layout.widget_steps)
            views.setTextViewText(R.id.widget_steps, if (goalReached) "✓" else "$steps")

            manager.updateAppWidget(widgetId, views)
        }
    }
}
