# Task Completion Checklist

When completing a development task in MySteps, ensure the following:

## Code Quality Checks
- [ ] **Build Success**: `./gradlew build` completes without errors
- [ ] **Lint Clean**: `./gradlew lint` passes with no critical issues
- [ ] **No Warnings**: Address or document any compiler warnings
- [ ] **Code Style**: Follows Kotlin conventions and project patterns

## Testing Requirements
- [ ] **Unit Tests**: Run `./gradlew test` and ensure all tests pass
- [ ] **Manual Testing**: Install on Wear OS device and verify functionality
- [ ] **Edge Cases**: Test hourly boundary transitions for step counting
- [ ] **Permissions**: Verify ACTIVITY_RECOGNITION permission handling

## Documentation Updates
- [ ] **KDoc Comments**: Add/update class and complex function documentation
- [ ] **Inline Comments**: Document non-obvious logic and business rules
- [ ] **Memory Files**: Update Serena memory if architecture changes

## Wear OS Specific Checks
- [ ] **Complications**: Test complication updates and refresh behavior
- [ ] **Background Service**: Verify StepCounterService runs correctly
- [ ] **Sensor Access**: Confirm step counter sensor registration
- [ ] **Battery Impact**: Consider power efficiency of changes
- [ ] **Hour Reset Logic**: Verify steps reset properly at hour boundaries

## Before Commit
- [ ] **Clean Build**: `./gradlew clean build` succeeds
- [ ] **Remove Debug Code**: Remove any temporary logging or debug code
- [ ] **Test on Device**: Physical Wear OS device testing completed
- [ ] **Logcat Review**: Check logs for errors: `adb logcat -s StepCounterService`

## Critical for Step Tracking Features
- [ ] **SharedPreferences**: Verify data persistence across app restarts
- [ ] **Hour Detection**: Test hour boundary transitions (mock or wait)
- [ ] **Step Calculation**: Verify hourly step count accuracy
- [ ] **Service Lifecycle**: Ensure service survives across different scenarios
