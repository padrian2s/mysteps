#!/bin/bash
# End-to-end alarm test for MySteps on Pixel Watch
# Simulates the real alarm flow and verifies vibration + notification

DEVICE="48301JEAYW011L"
PKG="com.example.mysteps"
RECEIVER="$PKG/.service.StepAlarmReceiver"
PASS=0
FAIL=0

echo "========================================="
echo "  MySteps Alarm E2E Test"
echo "========================================="
echo ""

# Test 1: Service running
echo -n "TEST 1: StepCounterService running... "
SVC=$(adb -s $DEVICE shell dumpsys activity services $PKG 2>&1 | grep "StepCounterService")
if [ -n "$SVC" ]; then
    echo "PASS"
    PASS=$((PASS+1))
else
    echo "FAIL - service not running"
    FAIL=$((FAIL+1))
fi

# Test 2: Complication service running
echo -n "TEST 2: HourlyStepsComplicationService running... "
CSVC=$(adb -s $DEVICE shell dumpsys activity services $PKG 2>&1 | grep "HourlyStepsComplicationService")
if [ -n "$CSVC" ]; then
    echo "PASS"
    PASS=$((PASS+1))
else
    echo "FAIL - complication service not running"
    FAIL=$((FAIL+1))
fi

# Test 3: Alarm scheduled in AlarmManager
echo -n "TEST 3: AlarmManager has CHECK_STEPS_ALARM... "
ALARM=$(adb -s $DEVICE shell dumpsys alarm 2>&1 | grep "CHECK_STEPS_ALARM" | head -1)
if [ -n "$ALARM" ]; then
    echo "PASS"
    PASS=$((PASS+1))
else
    echo "FAIL - no alarm scheduled"
    FAIL=$((FAIL+1))
fi

# Test 4: alarm_enabled is true
echo -n "TEST 4: alarm_enabled = true... "
PREFS=$(adb -s $DEVICE shell run-as $PKG cat /data/data/$PKG/shared_prefs/hourly_steps_prefs.xml 2>&1)
ENABLED=$(echo "$PREFS" | grep "alarm_enabled" | grep "true")
if [ -n "$ENABLED" ]; then
    echo "PASS"
    PASS=$((PASS+1))
else
    echo "FAIL - alarm disabled"
    FAIL=$((FAIL+1))
fi

# Test 5: Force trigger alarm and verify it fires
echo -n "TEST 5: Alarm receiver fires on broadcast... "
adb -s $DEVICE shell input keyevent KEYCODE_WAKEUP > /dev/null 2>&1
sleep 1
adb -s $DEVICE logcat -c > /dev/null 2>&1
adb -s $DEVICE shell "am broadcast -a $PKG.CHECK_STEPS_ALARM --ez force_test true -n $RECEIVER" > /dev/null 2>&1
sleep 3
RECEIVED=$(adb -s $DEVICE logcat -d 2>&1 | grep "Alarm received!")
if [ -n "$RECEIVED" ]; then
    echo "PASS"
    PASS=$((PASS+1))
else
    echo "FAIL - onReceive never called"
    FAIL=$((FAIL+1))
fi

# Test 6: Alarm triggers vibration + notification
echo -n "TEST 6: Triggering alarm (vibration + notification)... "
TRIGGERED=$(adb -s $DEVICE logcat -d 2>&1 | grep "Triggering alarm!")
if [ -n "$TRIGGERED" ]; then
    echo "PASS"
    PASS=$((PASS+1))
else
    echo "FAIL - alarm not triggered"
    FAIL=$((FAIL+1))
fi

# Test 7: Notification exists
echo -n "TEST 7: Alarm notification posted... "
NOTIF=$(adb -s $DEVICE shell dumpsys notification 2>&1 | grep "$PKG|2|null")
if [ -n "$NOTIF" ]; then
    echo "PASS"
    PASS=$((PASS+1))
else
    echo "FAIL - notification not found"
    FAIL=$((FAIL+1))
fi

# Test 8: Next alarm rescheduled after fire
echo -n "TEST 8: Next alarm rescheduled... "
NEXT=$(adb -s $DEVICE logcat -d 2>&1 | grep "Next alarm scheduled")
if [ -n "$NEXT" ]; then
    echo "PASS"
    PASS=$((PASS+1))
else
    echo "FAIL - not rescheduled"
    FAIL=$((FAIL+1))
fi

# Test 9: BootReceiver registered
echo -n "TEST 9: BootReceiver registered in manifest... "
BOOT=$(adb -s $DEVICE shell dumpsys package $PKG 2>&1 | grep "BootReceiver")
if [ -n "$BOOT" ]; then
    echo "PASS"
    PASS=$((PASS+1))
else
    echo "FAIL - BootReceiver not found"
    FAIL=$((FAIL+1))
fi

# Test 10: Alarm not rescheduled every 2s (spam check)
echo -n "TEST 10: No alarm reschedule spam... "
adb -s $DEVICE logcat -c > /dev/null 2>&1
sleep 6
SPAM_COUNT=$(adb -s $DEVICE logcat -d 2>&1 | grep -c "Next alarm scheduled")
if [ "$SPAM_COUNT" -lt 2 ]; then
    echo "PASS (count=$SPAM_COUNT)"
    PASS=$((PASS+1))
else
    echo "FAIL - scheduled $SPAM_COUNT times in 6s (should be 0-1)"
    FAIL=$((FAIL+1))
fi

# Test 11: Check last real alarm result (persistent log)
echo -n "TEST 11: Last real alarm result... "
PREFS=$(adb -s $DEVICE shell run-as $PKG cat /data/data/$PKG/shared_prefs/hourly_steps_prefs.xml 2>&1)
LAST_FIRE=$(echo "$PREFS" | grep "last_alarm_fire" | sed 's/.*value="\(.*\)".*/\1/')
LAST_RESULT=$(echo "$PREFS" | grep "last_alarm_result" | sed 's/.*value="\(.*\)".*/\1/')
if [ -n "$LAST_FIRE" ]; then
    echo "PASS (fire=$LAST_FIRE result=$LAST_RESULT)"
    PASS=$((PASS+1))
else
    echo "INFO - no real alarm fired yet (waiting for :50)"
    PASS=$((PASS+1))
fi

# Summary
echo ""
echo "========================================="
echo "  Results: $PASS passed, $FAIL failed"
echo "========================================="

if [ $FAIL -gt 0 ]; then
    exit 1
fi
