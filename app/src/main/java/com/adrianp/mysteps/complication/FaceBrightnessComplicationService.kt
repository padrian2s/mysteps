package com.adrianp.mysteps.complication

import android.content.ComponentName
import android.content.Context
import android.util.Log
import androidx.wear.watchface.complications.data.ComplicationData
import androidx.wear.watchface.complications.data.ComplicationType
import androidx.wear.watchface.complications.data.PlainComplicationText
import androidx.wear.watchface.complications.data.RangedValueComplicationData
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceUpdateRequester
import androidx.wear.watchface.complications.datasource.ComplicationRequest
import androidx.wear.watchface.complications.datasource.SuspendingComplicationDataSourceService
import com.adrianp.mysteps.service.StepCounterService

/**
 * Carries the Metro watch face's interactive brightness, set in the MySteps settings.
 * A Watch Face Format face has no code and can't read app settings; it reads this value
 * through a hidden, non-customizable complication slot and dims itself with it.
 */
class FaceBrightnessComplicationService : SuspendingComplicationDataSourceService() {

    override fun getPreviewData(type: ComplicationType): ComplicationData? =
        if (type == ComplicationType.RANGED_VALUE) data(DEFAULT_PERCENT) else null

    override suspend fun onComplicationRequest(request: ComplicationRequest): ComplicationData =
        data(get(this))

    private fun data(percent: Int) = RangedValueComplicationData.Builder(
        value = percent.toFloat(),
        min = 0f,
        max = 100f,
        contentDescription = PlainComplicationText.Builder("Watch face brightness $percent%").build()
    )
        .setText(PlainComplicationText.Builder("$percent%").build())
        .build()

    companion object {
        private const val KEY_FACE_BRIGHTNESS = "face_brightness_percent"
        const val DEFAULT_PERCENT = 30
        const val MIN_PERCENT = 5
        const val MAX_PERCENT = 100
        const val STEP_PERCENT = 5

        fun get(context: Context): Int =
            context.getSharedPreferences(StepCounterService.PREFS_NAME, Context.MODE_PRIVATE)
                .getInt(KEY_FACE_BRIGHTNESS, DEFAULT_PERCENT)

        fun set(context: Context, percent: Int) {
            context.getSharedPreferences(StepCounterService.PREFS_NAME, Context.MODE_PRIVATE)
                .edit()
                .putInt(KEY_FACE_BRIGHTNESS, percent.coerceIn(MIN_PERCENT, MAX_PERCENT))
                .apply()
            try {
                ComplicationDataSourceUpdateRequester
                    .create(
                        context = context,
                        complicationDataSourceComponent =
                            ComponentName(context, FaceBrightnessComplicationService::class.java)
                    )
                    .requestUpdateAll()
            } catch (e: Exception) {
                Log.e("FaceBrightness", "Failed to push brightness to the watch face", e)
            }
        }
    }
}
