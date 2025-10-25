# MySteps - Project Overview

## Purpose
MySteps is an Android Wear OS application that tracks hourly step count using the device's step counter sensor. The app provides:
- Watch face complications showing hourly steps
- Background step monitoring service
- Wear OS tiles for quick access
- Automatic hourly step reset

## Tech Stack
- **Language**: Kotlin
- **UI Framework**: Jetpack Compose for Wear OS
- **Build System**: Gradle with Kotlin DSL (.gradle.kts)
- **Target Platform**: Wear OS 3.0+ (minSdk 30, targetSdk 36)
- **Java Version**: Java 11
- **Key Libraries**:
  - androidx.wear.compose (Wear OS Compose UI)
  - androidx.wear.watchface.complications (Watch face complications)
  - androidx.wear.tiles (Wear OS tiles)
  - androidx.health:health-services-client (Step tracking)
  - Google Play Services Wearable
  - Horologist (Wear OS utilities)

## Project Structure
```
app/src/main/java/com/example/mysteps/
├── complication/          # Watch face complications
│   ├── HourlyStepsComplicationService.kt  # Hourly step counter complication
│   └── MainComplicationService.kt         # Main complication
├── service/               # Background services
│   └── StepCounterService.kt  # Continuous step monitoring with hourly reset
├── presentation/          # UI layer
│   ├── MainActivity.kt    # Main activity with complication refresh
│   └── theme/            # Compose theme
└── tile/                 # Wear OS tiles
    └── MainTileService.kt
```

## Key Features
1. **Hourly Step Tracking**: Counts steps within current hour, resets at hour boundary
2. **Background Service**: StepCounterService continuously monitors step sensor
3. **Watch Complications**: Integration with watch faces via complications
4. **Standalone App**: Runs independently on Wear OS without phone app

## Permissions Required
- ACTIVITY_RECOGNITION - For step counting
- BODY_SENSORS - Sensor access
- WAKE_LOCK - Background processing
