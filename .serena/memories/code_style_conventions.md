# Code Style and Conventions

## Naming Conventions
- **Classes**: PascalCase (e.g., `StepCounterService`, `MainActivity`)
- **Functions**: camelCase (e.g., `updateStepCount`, `getHourlySteps`)
- **Variables**: camelCase (e.g., `currentSteps`, `hourStartTime`)
- **Constants**: UPPER_SNAKE_CASE in companion objects (e.g., `KEY_HOUR_START_STEPS`, `PREFS_NAME`)
- **Packages**: lowercase (e.g., `com.example.mysteps.service`)

## File Organization
- One class per file
- File name matches class name
- Organize by feature/layer: complication/, service/, presentation/, tile/

## Code Documentation
- KDoc comments for classes explaining purpose and behavior
- Example:
```kotlin
/**
 * Background service that continuously monitors step count from the device sensor.
 * This service stores step data for hourly tracking.
 */
class StepCounterService : Service(), SensorEventListener {
```
- Inline comments for complex logic
- Clear variable names reducing need for comments

## Kotlin Style
- Use `lateinit` for late-initialized properties
- Prefer `val` over `var` when possible
- Use companion objects for constants and static methods
- Null safety: use `?` and `?.let` patterns
- String templates: `"New hour detected: $hour"`

## Compose UI Patterns
- Composable functions: PascalCase with `@Composable` annotation
- Preview functions: `@Preview` annotation with WearDevices
- Modifier chaining for UI styling
- Material Theme usage for consistent styling

## Architecture Patterns
- **Service Layer**: Background services for continuous operations
- **SharedPreferences**: For persistent data storage (hourly step tracking)
- **Singleton Access**: Static helper methods in companion objects
- **Coroutines**: For async operations (CoroutineScope, Dispatchers)

## Android Conventions
- Activities extend ComponentActivity
- Services implement appropriate interfaces (SensorEventListener)
- Proper lifecycle management (onCreate, onDestroy)
- Resource references via R class
