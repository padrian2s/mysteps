# Suggested Commands for MySteps Development

## Build Commands
```bash
# Build the project
./gradlew build

# Build debug APK
./gradlew assembleDebug

# Build release APK
./gradlew assembleRelease

# Clean build artifacts
./gradlew clean

# Clean and rebuild
./gradlew clean build
```

## Installation Commands
```bash
# Install debug build to connected Wear OS device
./gradlew installDebug

# Uninstall from device
./gradlew uninstallDebug

# Install and run
./gradlew installDebug && adb shell am start -n com.example.mysteps/.presentation.MainActivity
```

## Testing Commands
```bash
# Run unit tests
./gradlew test

# Run instrumented tests (requires connected device)
./gradlew connectedAndroidTest

# Run tests with reports
./gradlew test --info
```

## Code Quality Commands
```bash
# Run lint checks
./gradlew lint

# Generate lint report (HTML)
./gradlew lintDebug

# Format code (if ktlint configured)
./gradlew ktlintFormat
```

## Debugging Commands
```bash
# View logcat filtered for MySteps
adb logcat -s StepCounterService MainActivity HourlyStepsComplicationService

# Clear app data
adb shell pm clear com.example.mysteps

# List installed packages
adb shell pm list packages | grep mysteps

# Check permissions
adb shell dumpsys package com.example.mysteps | grep permission
```

## Gradle Tasks
```bash
# List all available tasks
./gradlew tasks

# Show project dependencies
./gradlew dependencies

# Show project properties
./gradlew properties
```

## Development Workflow
```bash
# Typical development cycle:
1. Make code changes
2. ./gradlew clean build          # Build and verify
3. ./gradlew installDebug          # Install to device
4. adb logcat -s StepCounterService # Monitor logs
```

## macOS Specific Notes
- Use `./gradlew` (not `gradle`) to use the project's Gradle wrapper
- Ensure Android SDK is properly configured in ANDROID_HOME or local.properties
- Use `adb` from Android SDK platform-tools (should be in PATH)
