# MySteps

**Hourly step tracking complications for Wear OS - finally filling the gap Google left for years.**

## Why This App Exists

Google Fit and Google Health have **never provided hourly step count complications** despite years of user requests. If you want to track your steps per hour on your watch face, you've been out of luck - until now.

MySteps solves this problem by providing dedicated **hourly step counter complications** that display on your Wear OS watch face, letting you monitor your activity throughout the day at a glance.

## Features

### Primary Feature: Hourly Steps Complication
- **Hourly Step Counter**: See steps for the current hour directly on your watch face
- **Auto-Updating**: Refreshes every 5 minutes to keep data current
- **Tap to Refresh**: Manual refresh available when needed
- **Watch Face Integration**: Works with any Wear OS watch face that supports complications

### Additional Features
- **Daily Step Counter Complication**: Total steps for the day
- **Background Tracking**: Continuous step counting using Health Services API
- **Tiles Support**: Quick-access tile for at-a-glance information
- **Standalone**: Works independently without requiring a paired phone
- **Modern UI**: Built with Jetpack Compose for Wear OS

## Technical Details

### Requirements
- **Minimum SDK**: Android 11 (API 30) / Wear OS 3.0
- **Target SDK**: Android 14 (API 36)
- **Hardware**: Wear OS device with step counter sensor

### Permissions
- `ACTIVITY_RECOGNITION`: For accessing step counter data
- `BODY_SENSORS`: For reading sensor data
- `WAKE_LOCK`: For background step tracking

### Architecture
```
com.example.mysteps/
├── complication/
│   ├── MainComplicationService.kt          # Primary step counter complication
│   └── HourlyStepsComplicationService.kt   # Hourly updating complication
├── service/
│   └── StepCounterService.kt               # Background step tracking service
├── tile/
│   └── MainTileService.kt                  # Tile for quick access
└── presentation/
    ├── MainActivity.kt                      # Main app activity
    └── theme/
        └── Theme.kt                         # Material theme configuration
```

### Technology Stack
- **Language**: Kotlin
- **UI Framework**: Jetpack Compose for Wear OS
- **Step Tracking**: Health Services Client 1.1.0-alpha04
- **Wear OS Components**:
  - Complications Data Source
  - Tiles API
  - Horologist library for enhanced Wear OS development

## Installation

### Building from Source
1. Clone the repository
2. Open the project in Android Studio
3. Connect your Wear OS device or start an emulator
4. Run the app using the standard Android Studio build process

```bash
./gradlew assembleDebug
```

## Usage

### Adding the Hourly Steps Complication (Primary Use Case)
1. Long-press on your watch face
2. Tap "Customize" or the settings icon
3. Select a complication slot
4. Choose **"MySteps Hourly"** from the list
5. Your hourly step count will now display on your watch face
6. Tap the complication anytime to manually refresh the data

### Adding the Daily Steps Complication
1. Follow the same steps above
2. Choose **"MySteps"** (instead of "MySteps Hourly") for total daily steps

### Adding Tiles
1. Swipe left from your watch face
2. Scroll to the end and tap "+"
3. Select "MySteps" from the list
4. The tile will show your current step count

### Viewing in App
- Open the MySteps app from your app drawer
- The main screen displays your current step information

## Development

### Build Configuration
- **Compile SDK**: 36
- **Java Version**: 11
- **Kotlin Compose**: Enabled
- **ProGuard**: Disabled in debug builds

### Key Dependencies
- Wear Compose Material
- Play Services Wearable
- Health Services Client
- Androidx Tiles
- Androidx Watchface Complications

## Version
- **Version Code**: 1
- **Version Name**: 1.0

## License
This project is currently unlicensed. Please contact the author for usage permissions.

## Contributing
Contributions, issues, and feature requests are welcome. Please ensure all code follows the existing Kotlin coding standards and Jetpack Compose best practices.

## Notes

### About This Project
This app exists because **Google has failed to provide hourly step complications for years**, despite it being one of the most requested features in the Wear OS community. While Google Fit and Google Health track steps, they only offer daily totals as complications - making it impossible to monitor your hourly activity patterns directly on your watch face.

MySteps fills this gap with a simple, focused solution that does one thing well: **showing you how many steps you've taken in the current hour**.

### Technical Notes
- Configured as a standalone Wear OS app - no phone required
- Step counting continues in the background for accurate totals
- Hourly complication updates every 5 minutes automatically
- Daily complication updates on-demand when tapped
