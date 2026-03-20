# Privacy Policy — MySteps

**Last updated:** March 20, 2026

## Overview

MySteps is a Wear OS step tracking application that runs entirely on your watch. It does not collect, transmit, or share any personal data.

## Data Collection

MySteps does **NOT**:
- Collect personal information
- Send data to any server
- Use analytics or tracking
- Share data with third parties
- Require an account or login
- Access the internet

## Data Stored on Device

MySteps stores the following data **locally on your watch only**:
- Hourly step counts (from the device's built-in step counter sensor)
- User preferences (step goal, alarm settings, active hours interval)
- Alarm scheduling state

This data is stored in Android SharedPreferences and is not accessible to other apps.

## Permissions

MySteps requests the following permissions, used solely for on-device functionality:
- **ACTIVITY_RECOGNITION**: Read step counter sensor
- **BODY_SENSORS**: Access sensor hardware
- **VIBRATE**: Alarm vibration when step goal not reached
- **WAKE_LOCK**: Keep step tracking running
- **POST_NOTIFICATIONS**: Show alarm notifications
- **FOREGROUND_SERVICE**: Background step counting
- **RECEIVE_BOOT_COMPLETED**: Reschedule alarms after device restart
- **SCHEDULE_EXACT_ALARM**: Schedule hourly step check alarms

## Children's Privacy

MySteps does not knowingly collect information from children under 13.

## Changes

We may update this privacy policy. Changes will be posted in the app's repository.

## Contact

For questions about this privacy policy, please open an issue at:
https://github.com/padrian2s/mysteps/issues
