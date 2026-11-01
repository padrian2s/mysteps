#!/usr/bin/env python3
"""Generates src/main/res/raw/watchface.xml for the Metro watch face.

Edit this file, not the XML: every element exists twice (interactive and
always-on), which is too repetitive to maintain by hand.

    python3 metroface/generate_watchface.py

Always-on (ambient) rules, from Google's AoD guidance (<= 15% lit pixels,
measured as average luminance; colors count proportionally):
  * pure black background, so OLED pixels are off
  * time drawn as an outline only
  * badges become a dark ring with a dimmed number
  * the "UPTOWN / DOWNTOWN" line and seconds are hidden
Elements keep the same positions in both modes.
"""
from pathlib import Path

OUT = Path(__file__).parent / "src/main/res/raw/watchface.xml"

SIZE = 452                      # canvas; the design's pixel positions carry over 1:1
BG = "#ff0e0e0e"                # interactive background
D, GAP, BADGE_Y = 64, 12, 106   # badge diameter, spacing, row top
RING = 3                        # ring stroke width
X0 = (SIZE - (4 * D + 3 * GAP)) // 2
BADGE_X = [X0 + i * (D + GAP) for i in range(4)]

# Badge colors: (interactive fill, ambient ring, ambient number)
RED = ("#ffee352e", "#ff6a1714", "#ffa8433f")
GREEN = ("#ff00933c", "#ff00421b", "#ff2f8f55")
ORANGE = ("#ffff6319", "#ff70290b", "#ffb0592e")
YELLOW = ("#fffccc0a", "#ff6b5704", "#ffa89030")
BLUE_RING = "#ff1a3370"
DIM_TEXT = "#ff8a8a8a"

AMBIENT_HIDE = '<Variant mode="AMBIENT" target="alpha" value="0" />'
AMBIENT_SHOW = '<Variant mode="AMBIENT" target="alpha" value="255" />'

# English names, measured in Inter at 26px (bold days with -0.5px tracking,
# regular months) so the date row can be centered without a layout engine
DAYS = ["SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"]
DAY_W = [110, 118, 122, 168, 142, 93, 142]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
MONTH_W = [53, 48, 58, 52, 59, 54, 49, 56, 50, 56, 58, 54]


def indent(text, n):
    pad = " " * n
    return "\n".join(pad + line if line.strip() else line for line in text.split("\n"))


def chain(source, values, quote=False):
    """Nested ternary: source == 1 ? v1 : (source == 2 ? v2 : ... vN)."""
    fmt = (lambda v: f"&quot;{v}&quot;") if quote else str
    expr = fmt(values[-1])
    for i in range(len(values) - 2, -1, -1):
        expr = f"({source} == {i + 1} ? {fmt(values[i])} : {expr})"
    return expr


def circle(color, ambient=None, x=0, d=D):
    """Filled circle (interactive only), or a ring (ambient only) when ambient=ring color."""
    if ambient:
        r = RING / 2
        return f"""<PartDraw x="{x}" y="0" width="{d}" height="{d}" alpha="0">
  {AMBIENT_SHOW}
  <Ellipse x="{r}" y="{r}" width="{d - RING}" height="{d - RING}">
    <Stroke color="{ambient}" thickness="{RING}" />
  </Ellipse>
</PartDraw>"""
    return f"""<PartDraw x="{x}" y="0" width="{d}" height="{d}">
  {AMBIENT_HIDE}
  <Ellipse x="0" y="0" width="{d}" height="{d}">
    <Fill color="{color}" />
  </Ellipse>
</PartDraw>"""


def text(content, size, color, x=0, pad=4, auto=True, ambient=False, spacing=None):
    """Centered number inside a badge. ambient=True: shown only in always-on."""
    variant = AMBIENT_SHOW if ambient else AMBIENT_HIDE
    alpha = ' alpha="0"' if ambient else ""
    auto_attr = ' isAutoSize="TRUE"' if auto else ""
    ls = f' letterSpacing="{spacing}"' if spacing else ""
    return f"""<PartText x="{x + pad}" y="0" width="{D - 2 * pad}" height="{D}"{alpha}>
  {variant}
  <Text align="CENTER"{auto_attr}>
    <Font family="inter_bold" size="{size}"{ls} color="{color}">{content}</Font>
  </Text>
</PartText>"""


def badge_texts(content, fallback, condition, colors, x, size, spacing=None, number_color="#ffffffff"):
    """Interactive + ambient number for a non-complication badge, '--' when no data."""
    name, expr = condition
    on = "\n".join([
        text(content, size, number_color, x, pad=2, spacing=spacing),
        text(content, size, colors[2], x, pad=2, spacing=spacing, ambient=True),
    ])
    off = "\n".join([
        text(fallback, 30, number_color, x, auto=False),
        text(fallback, 30, colors[2], x, auto=False, ambient=True),
    ])
    return f"""<Condition>
  <Expressions>
    <Expression name="{name}">{expr}</Expression>
  </Expressions>
  <Compare expression="{name}">
{indent(on, 4)}
  </Compare>
  <Default>
{indent(off, 4)}
  </Default>
</Condition>"""


def progress(fraction, colors):
    """Progress ring: white over a faint track; in ambient a dim arc over the dark ring."""
    r = D - 8
    arc = lambda color, ambient: f"""<PartDraw x="0" y="0" width="{D}" height="{D}"{' alpha="0"' if ambient else ''}>
  {AMBIENT_SHOW if ambient else AMBIENT_HIDE}
  <Arc centerX="{D // 2}" centerY="{D // 2}" width="{D - RING if ambient else r}" height="{D - RING if ambient else r}" startAngle="0" endAngle="0">
    <Transform target="endAngle" value="{fraction} * 360" />
    <Stroke color="{color}" thickness="{RING}" cap="ROUND" />
  </Arc>
</PartDraw>"""
    track = f"""<PartDraw x="0" y="0" width="{D}" height="{D}">
  {AMBIENT_HIDE}
  <Ellipse x="4" y="4" width="{r}" height="{r}">
    <Stroke color="#55ffffff" thickness="{RING}" />
  </Ellipse>
</PartDraw>"""
    return "\n".join([track, arc("#ffffffff", False), arc(colors[2], True)])


RANGED = ("(clamp([COMPLICATION.RANGED_VALUE_VALUE], [COMPLICATION.RANGED_VALUE_MIN], "
          "[COMPLICATION.RANGED_VALUE_MAX]) - [COMPLICATION.RANGED_VALUE_MIN]) / "
          "([COMPLICATION.RANGED_VALUE_MAX] - [COMPLICATION.RANGED_VALUE_MIN])")
GOAL = "clamp([COMPLICATION.GOAL_PROGRESS_VALUE] / [COMPLICATION.GOAL_PROGRESS_TARGET_VALUE], 0, 1)"
COMP_TEXT = '<Template>%s<Parameter expression="[COMPLICATION.TEXT]" /></Template>'


def complication_slot(slot_id, x, colors, label, provider, comment):
    def body(kind, *parts):
        return f"""<Complication type="{kind}">
{indent(chr(10).join(parts), 2)}
</Complication>"""

    bg = [circle(colors[0]), circle(None, ambient=colors[1])]
    numbers = lambda size, pad, auto=True: [
        text(COMP_TEXT if auto else "--", size, "#ffffffff", pad=pad, auto=auto),
        text(COMP_TEXT if auto else "--", size, colors[2], pad=pad, auto=auto, ambient=True),
    ]
    complications = "\n".join([
        body("RANGED_VALUE", *bg, progress(RANGED, colors), *numbers(30, 8)),
        body("GOAL_PROGRESS", *bg, progress(GOAL, colors), *numbers(30, 8)),
        body("SHORT_TEXT", *bg, *numbers(34, 4)),
        body("EMPTY", *bg, *numbers(30, 4, auto=False)),
    ])
    return f"""<!-- {comment} -->
<ComplicationSlot x="{x}" y="{BADGE_Y}" width="{D}" height="{D}" slotId="{slot_id}"
    displayName="{label}" supportedTypes="RANGED_VALUE GOAL_PROGRESS SHORT_TEXT EMPTY">
  <DefaultProviderPolicy
      primaryProvider="{provider}"
      primaryProviderType="RANGED_VALUE"
      defaultSystemProvider="EMPTY"
      defaultSystemProviderType="EMPTY" />
  <BoundingOval x="0" y="0" width="{D}" height="{D}" />
{indent(complications, 2)}
</ComplicationSlot>"""


def rule(name, y, height, color):
    """Full-width line, dimmed in ambient."""
    return f"""<!-- {name} -->
<PartDraw x="0" y="{y}" width="{SIZE}" height="{height}" name="{name}">
  <Variant mode="AMBIENT" target="alpha" value="70" />
  <Rectangle x="0" y="0" width="{SIZE}" height="{height}">
    <Fill color="{color}" />
  </Rectangle>
</PartDraw>"""


HOUR = "[IS_24_HOUR_MODE] ? [HOUR_0_23_Z] : [HOUR_1_12]"


def clocks():
    interactive = lambda width, align: f"""<DigitalClock x="0" y="182" width="{SIZE}" height="132">
  {AMBIENT_HIDE}
  <TimeText format="hh:mm" hourFormat="SYNC_TO_DEVICE" align="{align}"
      x="0" y="0" width="{width}" height="132">
    <Font family="inter_bold" size="132" color="#ffffffff" />
  </TimeText>
</DigitalClock>"""
    seconds = """<DigitalClock x="0" y="182" width="452" height="132">
  <TimeText format="ss" align="START" x="390" y="86" width="40" height="34">
    <Variant mode="AMBIENT" target="alpha" value="0" />
    <Font family="inter_bold" size="28" color="#ffa7a9ac" />
  </TimeText>
</DigitalClock>"""
    return f"""<!-- Time. With seconds on, time and seconds are centered together. -->
<BooleanConfiguration id="showSeconds">
  <BooleanOption id="FALSE">
{indent(interactive(SIZE, "CENTER"), 4)}
  </BooleanOption>
  <BooleanOption id="TRUE">
    <Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="TimeAndSeconds">
{indent(interactive(384, "END"), 6)}
{indent(seconds, 6)}
    </Group>
  </BooleanOption>
</BooleanConfiguration>

<!-- Always-on time: outline only, black inside -->
<PartText x="0" y="182" width="{SIZE}" height="132" name="AmbientTime" alpha="0">
  {AMBIENT_SHOW}
  <Text align="CENTER">
    <Font family="inter_bold" size="132" color="#ff000000">
      <Outline color="#ffffffff" width="2">
        <Template>%s:%s
          <Parameter expression="{HOUR}" />
          <Parameter expression="[MINUTE_Z]" />
        </Template>
      </Outline>
    </Font>
  </Text>
</PartText>"""


def date_row():
    day_w = chain("[DAY_OF_WEEK]", DAY_W)
    month_w = chain("[MONTH]", MONTH_W)
    dim = '<Variant mode="AMBIENT" target="alpha" value="150" />'
    return f"""<!-- Date row: [day badge] DAYNAME MON, centered from the measured widths -->
<Group x="0" y="336" width="400" height="34" name="DateRow">
  <Transform target="x" value="({SIZE} - (58 + {day_w} + 12 + {month_w})) / 2" />
{indent(circle("#ff0039a6", d=34), 2)}
{indent(circle(None, ambient=BLUE_RING, d=34), 2)}
  <PartText x="0" y="0" width="34" height="34">
    {dim}
    <Text align="CENTER">
      <Font family="inter_bold" size="18" color="#ffffffff">
        <Template>%s<Parameter expression="[DAY]" /></Template>
      </Font>
    </Text>
  </PartText>
  <PartText x="46" y="0" width="180" height="34">
    {dim}
    <Text align="START">
      <Font family="inter_bold" size="26" letterSpacing="-0.019" color="#ffffffff">
        <Template>%s<Parameter expression="{chain('[DAY_OF_WEEK]', DAYS, quote=True)}" /></Template>
      </Font>
    </Text>
  </PartText>
  <PartText x="160" y="0" width="80" height="34">
    <Transform target="x" value="58 + {day_w}" />
    {dim}
    <Text align="START">
      <Font family="inter_regular" size="26" color="#ffa7a9ac">
        <Template>%s<Parameter expression="{chain('[MONTH]', MONTHS, quote=True)}" /></Template>
      </Font>
    </Text>
  </PartText>
</Group>"""


def direction():
    return f"""<!-- Direction line (hidden in always-on): morning goes uptown, evening downtown -->
<PartText x="0" y="384" width="{SIZE}" height="18" name="Direction">
  {AMBIENT_HIDE}
  <Text align="CENTER">
    <Font family="inter_bold" size="12" letterSpacing="0.167" color="#ffa7a9ac">
      <Template>%s<Parameter expression="[HOUR_0_23] &lt; 12 ? &quot;UPTOWN ↑ MORNING&quot; : &quot;DOWNTOWN ↓ EVENING&quot;" /></Template>
    </Font>
  </Text>
</PartText>"""


def badges():
    hr, temp = BADGE_X[0], BADGE_X[3]
    parts = [
        "<!-- Heart rate -->",
        circle(RED[0], x=hr), circle(None, ambient=RED[1], x=hr),
        badge_texts('<Template>%s<Parameter expression="round([HEART_RATE])" /></Template>', "--",
                    ("hasHr", "[HEART_RATE] &gt; 0"), RED, hr, 42, spacing="-0.04"),
        "<!-- Temperature -->",
        circle(YELLOW[0], x=temp), circle(None, ambient=YELLOW[1], x=temp),
        badge_texts('<Template>%s°<Parameter expression="[WEATHER.TEMPERATURE]" /></Template>', "--",
                    ("hasWeather", "[WEATHER.IS_AVAILABLE]"), YELLOW, temp, 30, spacing="-0.045",
                    number_color="#ff0e0e0e"),
    ]
    return f"""<!-- Four round "line" badges: heart rate, active zone minutes, MySteps, temperature -->
<Group x="0" y="{BADGE_Y}" width="{SIZE}" height="{D}" name="Badges">
{indent(chr(10).join(parts), 2)}
</Group>"""


def watchface():
    scene = "\n\n".join([
        f"""<!-- Interactive background; pure black in always-on (OLED pixels off) -->
<PartDraw x="0" y="0" width="{SIZE}" height="{SIZE}" name="Background">
  {AMBIENT_HIDE}
  <Rectangle x="0" y="0" width="{SIZE}" height="{SIZE}">
    <Fill color="{BG}" />
  </Rectangle>
</PartDraw>""",
        rule("TopRule", 78, 4, "#ffffffff"),
        badges(),
        complication_slot(2, BADGE_X[1], GREEN, "azm_slot_label",
                          "com.fitbit.FitbitMobile/com.google.android.wearable.fitbit.mainapp.complications.offloadable.azm.OffloadableAZMComplicationDataSourceService",
                          "Active Zone Minutes (Fitbit complication by default)"),
        complication_slot(0, BADGE_X[2], ORANGE, "mysteps_slot_label",
                          "com.adrianp.mysteps/com.adrianp.mysteps.complication.HourlyStepsComplicationService",
                          "MySteps: steps this hour, ❤N/M once the goal is met"),
        clocks(),
        rule("Divider", 322, 2, "#ff3a3a3a"),
        date_row(),
        direction(),
    ])
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!-- GENERATED by metroface/generate_watchface.py — edit that file, not this one. -->
<WatchFace width="{SIZE}" height="{SIZE}" clipShape="CIRCLE">
  <Metadata key="CLOCK_TYPE" value="DIGITAL" />
  <Metadata key="PREVIEW_TIME" value="10:08:32" />

  <UserConfigurations>
    <BooleanConfiguration id="showSeconds" displayName="show_seconds_label"
        screenReaderText="show_seconds_label" defaultValue="FALSE" />
  </UserConfigurations>

  <Scene backgroundColor="#ff000000">
{indent(scene, 4)}
  </Scene>
</WatchFace>
"""


if __name__ == "__main__":
    OUT.write_text(watchface())
    print(f"wrote {OUT}")
