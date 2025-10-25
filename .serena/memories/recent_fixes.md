# Recent Fixes

## SharedPreferences Not Saving - Critical Bug (2025-10-25)

### Problem from Logcat
```
Hour baseline reset to: 36107
Steps updated - Total: 36107, HourStart: 0, Hourly: 0
```

The code logged "baseline reset to 36107" but immediately read back 0! **SharedPreferences wasn't saving**.

### Root Cause
**Confused Kotlin `.apply { }` scope function with SharedPreferences.Editor `.apply()` method!**

**Wrong code** (doesn't save):
```kotlin
prefs.edit().apply {
    putLong(KEY_HOUR_START_STEPS, totalSteps)
    putLong(KEY_HOUR_START_TIME, calendar.timeInMillis)
    putInt(KEY_CURRENT_HOUR, hour)
}
// Returns the Editor object, but NEVER calls Editor.apply() to save!
```

**What was happening:**
- `.apply { }` is a **scope function** that runs the block and returns the receiver
- It does NOT call the `SharedPreferences.Editor.apply()` method
- No data was ever saved!

### Solution
**Use method chaining with `.apply()` at the end:**

```kotlin
prefs.edit()
    .putLong(KEY_HOUR_START_STEPS, totalSteps)
    .putLong(KEY_HOUR_START_TIME, calendar.timeInMillis)
    .putInt(KEY_CURRENT_HOUR, hour)
    .apply()  // ✅ Calls Editor.apply() to save
```

**Fixed in 2 methods:**

1. **onCreate()** (lines 72-75):
```kotlin
prefs.edit()
    .putInt(KEY_CURRENT_HOUR, currentActualHour)
    .putLong(KEY_HOUR_START_TIME, calendar.timeInMillis)
    .apply()
```

2. **updateStepCount()** (lines 109-113, 119-122, 126-129):
```kotlin
// Hour change
prefs.edit()
    .putLong(KEY_HOUR_START_STEPS, totalSteps)
    .putLong(KEY_HOUR_START_TIME, calendar.timeInMillis)
    .putInt(KEY_CURRENT_HOUR, hour)
    .apply()

// First sensor reading
prefs.edit()
    .putLong(KEY_HOUR_START_STEPS, totalSteps)
    .putLong(KEY_HOUR_START_TIME, calendar.timeInMillis)
    .apply()

// Update current steps
prefs.edit()
    .putLong(KEY_CURRENT_STEPS, totalSteps)
    .putLong(KEY_LAST_UPDATE, System.currentTimeMillis())
    .apply()
```

### Technical Details
**Kotlin has TWO different `apply`:**
1. **Scope function** `.apply { }`: Runs block with `this = receiver`, returns receiver
2. **Editor method** `.apply()`: Saves SharedPreferences asynchronously

**Correct patterns:**
```kotlin
// Method chaining (RECOMMENDED)
prefs.edit()
    .putLong(KEY, value)
    .apply()

// Scope function with manual apply
prefs.edit().also {
    it.putLong(KEY, value)
    it.apply()  // Must call explicitly!
}
```

**Wrong patterns:**
```kotlin
// ❌ WRONG - Never saves!
prefs.edit().apply {
    putLong(KEY, value)
}

// ❌ WRONG - Double apply (my earlier "fix")
prefs.edit().apply {
    putLong(KEY, value)
    apply()  // This was the right idea, but confusing
}
```

### Expected Logs After Fix
```
Service created
Restored hour from storage: 10
New hour detected: 11 (previous: 10)
Hour baseline reset to: 36107
Steps updated - Total: 36107, HourStart: 36107, Hourly: 0  ✅
Steps updated - Total: 36108, HourStart: 36107, Hourly: 1  ✅
Steps updated - Total: 36109, HourStart: 36107, Hourly: 2  ✅
```

---

## Hour Change Detection Conflict (2025-10-25)

### Problem from Logcat
```
Hour changed on service start: 10 -> 11. Resetting baseline.
Steps updated - Total: 36040, HourStart: 0, Hourly: 0
```

Even though the hour changed and baseline should be 36040, it was showing 0.

### Root Cause
**Race condition between onCreate() and updateStepCount():**

1. `onCreate()` detected hour change (10→11) and set `currentHour = 11`
2. First sensor reading arrives with `hour = 11`
3. `updateStepCount()` checks `if (hour != currentHour)` → `11 != 11` → **FALSE!**
4. Baseline never gets set to the actual sensor value

### Solution
**onCreate() now restores OLD hour, letting updateStepCount() detect the change:**

```kotlin
if (storedHour == -1) {
    // First time only
    currentHour = currentActualHour
} else {
    // Restore the OLD hour from storage
    currentHour = storedHour  // ✅ e.g., restores 10
}
```

**updateStepCount() detects change on first sensor reading:**
```kotlin
if (hour != currentHour) {
    // Now detects 11 != 10 ✅
    prefs.edit()
        .putLong(KEY_HOUR_START_STEPS, totalSteps)
        .apply()
}
```

---

## Hourly Step Calculation Bug Fix (2025-10-25)

### Problem
Steps were counting but hourly always showed 0.

### Root Cause
Wrong default value in `getHourlySteps()`:
```kotlin
val hourStartSteps = prefs.getLong(KEY_HOUR_START_STEPS, currentSteps)
// When missing: currentSteps - currentSteps = 0 ❌
```

### Solution
```kotlin
val hourStartSteps = prefs.getLong(KEY_HOUR_START_STEPS, 0)
// When missing: currentSteps - 0 = currentSteps ✅
```

---

## Heart Icon Goal Feature (2025-10-25)

### Feature
Display heart icon (❤) at 250+ steps per hour.

### Implementation
Modified `HourlyStepsComplicationService.kt`:
```kotlin
val text = if (showError) {
    "--"
} else if (steps >= 250) {
    "❤"
} else {
    steps.toString()
}
```

### User Experience
- **0-249 steps**: Shows step count
- **250+ steps**: Shows ❤
- **Hourly reset**: Heart disappears at new hour