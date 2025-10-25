# Architecture and Design Notes

## Step Tracking Architecture

### Hour-Based Step Counting
The app implements hourly step reset using a baseline approach:
1. **Sensor Type**: Uses `TYPE_STEP_COUNTER` (cumulative since device boot)
2. **Baseline Tracking**: Stores baseline step count at start of each hour
3. **Hourly Calculation**: `hourly_steps = current_steps - hour_start_steps`
4. **Hour Detection**: Compares `Calendar.HOUR_OF_DAY` to detect hour changes

### Data Persistence
Uses SharedPreferences with keys:
- `KEY_HOUR_START_STEPS`: Baseline step count at hour start
- `KEY_HOUR_START_TIME`: Timestamp of hour start
- `KEY_CURRENT_STEPS`: Latest total step count from sensor
- `KEY_LAST_UPDATE`: Last update timestamp

### Service Architecture
**StepCounterService**:
- Background service with `START_STICKY` (auto-restart)
- Implements `SensorEventListener` for step sensor events
- Registers sensor with `SENSOR_DELAY_NORMAL`
- Maintains current hour state to detect transitions
- Updates SharedPreferences on each sensor event

**Lifecycle**: Started by HourlyStepsComplicationService when complication activates

### Complication Pattern
**HourlyStepsComplicationService**:
- Extends `SuspendingComplicationDataSourceService`
- Supports `ComplicationType.SHORT_TEXT`
- Update period: 300 seconds (5 minutes)
- Reads data from StepCounterService SharedPreferences
- Tap action: Opens MainActivity to refresh complication

### Known Limitations
1. **Hour Boundary Reset**: Currently checks hour on sensor events only
   - If no steps during hour transition, may not reset until next step
   - Solution: Could use AlarmManager for guaranteed hourly checks
2. **Device Boot**: Step counter resets to 0 on device restart
   - Service handles this by resetting baseline
3. **Permission Required**: ACTIVITY_RECOGNITION needed for sensor access

## Design Patterns Used
- **Service Pattern**: Background step monitoring
- **Observer Pattern**: Sensor event listening
- **Singleton Access**: Static helper methods in companion objects
- **Repository Pattern**: SharedPreferences as data layer
- **Compose UI**: Declarative UI with preview support

## Future Considerations
- Consider WorkManager for periodic hour checks
- Add step history storage (daily/weekly aggregates)
- Implement notification for hourly goals
- Add complication for daily step total
