#!/usr/bin/env python3
"""Generates src/main/res/raw/watchface.xml for the Neo watch face.

Edit this file, not the XML:

    python3 neoface/generate_watchface.py

The layout follows the "Cadran Neo" design (450 px HTML mock-up, Unbounded + Inter),
scaled to the Pixel Watch 3's 456 px: an outer ring of 60 segments (one per second)
lit in violet for the Active Zone Minutes done of the goal, the current second's
segment white; a thin lime inner ring for MySteps' steps this hour; a pill on top
with the weekday, date and temperature; the time stacked big (hours ink, minutes
lime); zone minutes (left) and steps (right) at mid-height; a heart rate pill at the
bottom colored by zone. Not offloadable, so raising the wrist wakes Android and
MySteps refreshes.
"""
import math
from pathlib import Path
from fontTools.ttLib import TTFont

HERE = Path(__file__).parent
RES = HERE / "src/main/res"
OUT = RES / "raw/watchface.xml"

SIZE = 456
K = SIZE / 450                   # design px -> watch px
C = SIZE / 2


def s(v):
    """Design size to watch size (rounded to 0.1 px)."""
    return round(v * K, 1)


def p(v):
    """Design coordinate (x or y) to watch coordinate."""
    return round(C + (v - 225) * K, 1)


INK, LIME, VIOLET, AMBER, RED = "#fff2f0ea", "#ffc8ff3d", "#ffa99cff", "#ffffb020", "#ffff5a4f"
BLACK = "#ff000000"

# Heart rate zones as in the design: rest < 100, active 100-129, cardio >= 130
# (id, condition, pill color, text color, heart color, label, bpm sample for the width)
HR_ACTIVE, HR_CARDIO = 100, 130
ZONES = [("hrRest", f"[HEART_RATE] &gt; 0 &amp;&amp; [HEART_RATE] &lt; {HR_ACTIVE}",
          "#ff22242b", INK, RED, "REPAUS", "89"),
         ("hrActive", f"[HEART_RATE] &gt;= {HR_ACTIVE} &amp;&amp; [HEART_RATE] &lt; {HR_CARDIO}",
          AMBER, BLACK, BLACK, "ACTIV", "129"),
         ("hrCardio", f"[HEART_RATE] &gt;= {HR_CARDIO}", RED, BLACK, BLACK, "CARDIO", "189"),
         ("noHr", "[HEART_RATE] &lt;= 0", "#ff22242b", INK, RED, "REPAUS", "--")]

DAYS = ["DUM", "LUN", "MAR", "MIE", "JOI", "VIN", "SÂM"]
MONTHS = ["IAN", "FEB", "MAR", "APR", "MAI", "IUN", "IUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
AMBIENT_HIDE = '<Variant mode="AMBIENT" target="alpha" value="0" />'
HR_ACTIVITY = "com.adrianp.mysteps/com.adrianp.mysteps.presentation.HeartRateActivity"

FONT_FILES = {n: TTFont(RES / "font" / f"{n}.ttf")
              for n in ("unbounded_time", "unbounded_bold", "inter_semibold")}
# Unbounded's and Inter's line boxes (hhea) are centered on their caps, so a text box
# centered on y puts the caps' middle on y, in the browser and on the watch alike.

# Rings (design px): outer 60 segments, inner steps ring
SEG_R, SEG_W, SEG_GAP = 214, 8, 5
SEG_HALF = (2 * math.pi * SEG_R / 60 - SEG_W - SEG_GAP) / 2 / SEG_R * 180 / math.pi   # degrees
SEG_DIM = 46                     # opacity .18
STEPS_R, STEPS_W = 201, 4
STEPS_TRACK = 36                 # opacity .14

# Text sizes (design px), above the mock-up's (10-22 px read badly on the wrist):
# side numbers 22 -> 28, labels 10 -> 13, date pill 12 -> 15, bpm 21 -> 28
TIME_SIZE, TIME_LINE = 138, 0.82
HOURS_CY, MINUTES_CY = 225 - TIME_SIZE * TIME_LINE / 2, 225 + TIME_SIZE * TIME_LINE / 2
SIDE_SIZE, LABEL_SIZE, LABEL_SPACING = 28, 13, 0.14
SIDE_GAP = 5
SIDE_NUM_CY = 225 - (SIDE_SIZE + SIDE_GAP + LABEL_SIZE) / 2 + SIDE_SIZE / 2
SIDE_LABEL_CY = 225 + (SIDE_SIZE + SIDE_GAP + LABEL_SIZE) / 2 - LABEL_SIZE / 2
SIDE_LEFT_X, SIDE_RIGHT_X = 28 + 40, 450 - 28 - 40
DATE_SIZE, DATE_SPACING, DATE_TOP = 15, 0.12, 52
BPM_SIZE, PILL_LABEL_SIZE, PILL_HEART = 28, 13, 21
PILL_BOTTOM = 396


def text_width(content, font, size, spacing=0.0):
    """Advance width in px, as the browser lays it out (letter-spacing after every glyph)."""
    f = FONT_FILES[font]
    cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    return sum(hmtx[cmap[ord(ch)]][0] / upm + spacing for ch in content) * size


def indent(text, n):
    pad = " " * n
    return "\n".join(pad + line if line.strip() else line for line in text.split("\n"))


def chain(source, values):
    """Nested ternary: source == 1 ? v1 : (source == 2 ? v2 : ... vN), quoted strings."""
    expr = f"&quot;{values[-1]}&quot;"
    for i in range(len(values) - 2, -1, -1):
        expr = f"({source} == {i + 1} ? &quot;{values[i]}&quot; : {expr})"
    return expr


def text(content, cx, cy, size, font="inter_semibold", color=INK, width=None, extra="",
         spacing=0.0, align="CENTER"):
    """Single-line text whose caps' middle sits on (cx, cy), watch px.
    align=START puts the left edge at cx, END the right edge."""
    w = round(width or SIZE)
    h = round(size * 1.6)
    x = {"CENTER": cx - w / 2, "START": cx, "END": cx - w}[align]
    ls = f' letterSpacing="{spacing:g}"' if spacing else ""
    return f"""<PartText x="{round(x)}" y="{round(cy - h / 2)}" width="{w}" height="{h}"{extra}>
  <Text align="{align}">
    <Font family="{font}" size="{size:g}" color="{color}"{ls}>{content}</Font>
  </Text>
</PartText>"""


def template(fmt, *exprs):
    params = "".join(f'<Parameter expression="{e}" />' for e in exprs)
    return f"<Template>{fmt}{params}</Template>"


def image(resource, x, y, w, h, tint=None):
    t = f' tintColor="{tint}"' if tint else ""
    return f"""<PartImage x="{round(x)}" y="{round(y)}" width="{round(w)}" height="{round(h)}"{t}>
  <Image resource="{resource}" />
</PartImage>"""


def arc(r, stroke, color, start=0, end=360, alpha=255, extra="", transform=""):
    """Full-screen arc on mid-radius r (watch px), degrees clockwise from 12 o'clock."""
    a = f' alpha="{alpha}"' if alpha != 255 else ""
    return f"""<PartDraw x="0" y="0" width="{SIZE}" height="{SIZE}"{a}>{extra}
  <Arc centerX="{C:g}" centerY="{C:g}" width="{2 * r:g}" height="{2 * r:g}" startAngle="{start:g}" endAngle="{end:g}">{transform}
    <Stroke color="{color}" thickness="{stroke:g}" cap="ROUND" />
  </Arc>
</PartDraw>"""


def pill(cx, cy, w, h, fill=None, stroke=None, extra=""):
    """Rounded box centered on (cx, cy), watch px, fully rounded ends."""
    x, y = math.floor(cx - w / 2), math.floor(cy - h / 2)
    W, H = math.ceil(w) + 2, math.ceil(h) + 2
    paint = f'\n    <Fill color="{fill}" />' if fill else ""
    if stroke:
        paint += f'\n    <Stroke color="{stroke[0]}" thickness="{stroke[1]:g}" />'
    o = stroke[1] / 2 if stroke else 0
    return f"""<PartDraw x="{x}" y="{y}" width="{W}" height="{H}"{extra}>
  <RoundRectangle x="{cx - w / 2 - x + o:g}" y="{cy - h / 2 - y + o:g}" width="{w - 2 * o:g}" height="{h - 2 * o:g}" cornerRadiusX="{(h - 2 * o) / 2:g}" cornerRadiusY="{(h - 2 * o) / 2:g}">{paint}
  </RoundRectangle>
</PartDraw>"""


def group(name, xml, extra=""):
    return f"""<Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="{name}">{extra}
{indent(xml, 2)}
</Group>"""


RANGED = ("(clamp([COMPLICATION.RANGED_VALUE_VALUE], [COMPLICATION.RANGED_VALUE_MIN], "
          "[COMPLICATION.RANGED_VALUE_MAX]) - [COMPLICATION.RANGED_VALUE_MIN]) / "
          "([COMPLICATION.RANGED_VALUE_MAX] - [COMPLICATION.RANGED_VALUE_MIN])")
GOAL = "[COMPLICATION.GOAL_PROGRESS_VALUE] / [COMPLICATION.GOAL_PROGRESS_TARGET_VALUE]"


def side_column(cx, color, label, value):
    """Number over its small label, centered on x = cx (design px)."""
    return "\n".join([
        text(value, p(cx), p(SIDE_NUM_CY), s(SIDE_SIZE), font="unbounded_bold", color=color,
             width=s(110)),
        text(label, p(cx), p(SIDE_LABEL_CY), s(LABEL_SIZE), color=INK, width=s(110),
             spacing=LABEL_SPACING, extra=' alpha="158"')])


def segments(fraction):
    """60 segments on the outer ring, centered on each second's mark; the first
    round(fraction * 60) lit (at least one once there is any), the rest dim."""
    lit = f"(({fraction}) &gt; 0 ? clamp(round(clamp({fraction}, 0, 1) * 60), 1, 60) : 0)" if fraction else "0"
    out = []
    for i in range(60):
        a = i * 6
        alpha = f'\n  <Transform target="alpha" value="{i} &lt; {lit} ? 255 : {SEG_DIM}" />' if fraction else ""
        dim = "" if fraction else f"\n  {AMBIENT_HIDE}"
        out.append(arc(s(SEG_R), s(SEG_W), VIOLET, a - SEG_HALF, a + SEG_HALF,
                       alpha=255 if fraction else SEG_DIM, extra=alpha + dim))
    return "\n".join(out)


def azm_slot():
    """Outer ring + left column: Active Zone Minutes (Fitbit) by default. The watch
    clips a complication to its bounding shape: a full-screen oval."""
    def body(kind, fraction, value):
        parts = [segments(fraction), side_column(SIDE_LEFT_X, VIOLET, "MIN", value)]
        return f"""<Complication type="{kind}">
{indent(group(kind, chr(10).join(parts)), 2)}
</Complication>"""
    return f"""<!-- Outer segmented ring + left number: Active Zone Minutes (Fitbit) by default -->
<ComplicationSlot x="0" y="0" width="{SIZE}" height="{SIZE}" slotId="1"
    displayName="azm_slot_label" supportedTypes="RANGED_VALUE GOAL_PROGRESS SHORT_TEXT EMPTY">
  <DefaultProviderPolicy
      primaryProvider="com.fitbit.FitbitMobile/com.google.android.wearable.fitbit.mainapp.complications.offloadable.azm.OffloadableAZMComplicationDataSourceService"
      primaryProviderType="RANGED_VALUE"
      defaultSystemProvider="EMPTY"
      defaultSystemProviderType="EMPTY" />
  <BoundingOval x="0" y="0" width="{SIZE}" height="{SIZE}" />
{indent(body("RANGED_VALUE", RANGED, template("%s", "[COMPLICATION.TEXT]")), 2)}
{indent(body("GOAL_PROGRESS", GOAL, template("%s", "[COMPLICATION.TEXT]")), 2)}
{indent(body("SHORT_TEXT", None, template("%s", "[COMPLICATION.TEXT]")), 2)}
{indent(body("EMPTY", None, "--"), 2)}
</ComplicationSlot>"""


def steps_slot():
    """Inner ring + right column: MySteps, steps this hour. MySteps sends value 0 of
    max 1 once the hour's goal is met: full ring then, and "❤N/M" without the ❤."""
    met = "[COMPLICATION.RANGED_VALUE_MAX] == 1"

    def ring(fraction):
        track = arc(s(STEPS_R), s(STEPS_W), LIME, alpha=STEPS_TRACK, extra=f"\n  {AMBIENT_HIDE}")
        if not fraction:
            return track
        progress = arc(s(STEPS_R), s(STEPS_W), LIME, extra=(
            f'\n  <Transform target="alpha" value="({fraction}) &gt; 0 ? 255 : 0" />'),
            transform=f'\n    <Transform target="endAngle" value="clamp({fraction}, 0, 1) * 360" />')
        return track + "\n" + progress

    def body(kind, fraction, value):
        parts = [ring(fraction), side_column(SIDE_RIGHT_X, LIME, "PAȘI", value)]
        return f"""<Complication type="{kind}">
{indent(group(kind, chr(10).join(parts)), 2)}
</Complication>"""
    label = template("%s", f"{met} ? subText([COMPLICATION.TEXT], 1, textLength([COMPLICATION.TEXT])) "
                           f": [COMPLICATION.TEXT]")
    o = round(C - s(STEPS_R + STEPS_W / 2 + 1) - 1)
    return f"""<!-- Inner ring + right number: MySteps, steps this hour -->
<ComplicationSlot x="0" y="0" width="{SIZE}" height="{SIZE}" slotId="0"
    displayName="mysteps_slot_label" supportedTypes="RANGED_VALUE GOAL_PROGRESS SHORT_TEXT EMPTY">
  <DefaultProviderPolicy
      primaryProvider="com.adrianp.mysteps/com.adrianp.mysteps.complication.HourlyStepsComplicationService"
      primaryProviderType="RANGED_VALUE"
      defaultSystemProvider="EMPTY"
      defaultSystemProviderType="EMPTY" />
  <BoundingOval x="{o}" y="{o}" width="{SIZE - 2 * o}" height="{SIZE - 2 * o}" />
{indent(body("RANGED_VALUE", f"({met} ? 1 : {RANGED})", label), 2)}
{indent(body("GOAL_PROGRESS", GOAL, template("%s", "[COMPLICATION.TEXT]")), 2)}
{indent(body("SHORT_TEXT", None, template("%s", "[COMPLICATION.TEXT]")), 2)}
{indent(body("EMPTY", None, "--"), 2)}
</ComplicationSlot>"""


def second_segment():
    """The current second's segment, white, over the outer ring (hidden in always-on)."""
    seg = arc(s(SEG_R), s(SEG_W), INK, -SEG_HALF, SEG_HALF)
    return f"""<!-- Current second: white segment -->
<Group x="0" y="0" width="{SIZE}" height="{SIZE}" pivotX="0.5" pivotY="0.5" name="Second">
  <Transform target="angle" value="[SECOND] * 6" />
  {AMBIENT_HIDE}
{indent(seg, 2)}
</Group>"""


def date_pill():
    """Weekday, day and month · temperature (amber) in an outlined pill; without
    weather only the date."""
    date = template("%s %s %s", chain("[DAY_OF_WEEK]", DAYS), "[DAY]", chain("[MONTH]", MONTHS))
    temp = template("%s°", "[WEATHER.TEMPERATURE]")
    date_w = text_width("MIE 28 NOV", "inter_semibold", DATE_SIZE, DATE_SPACING)
    temp_w = text_width("25°", "inter_semibold", DATE_SIZE, DATE_SPACING)
    h = 6 + DATE_SIZE + 6 + 2
    cy = DATE_TOP + h / 2
    border = ("#3df2f0ea", s(1))          # rgba(242,240,234,.24)

    def with_weather():
        w = 13 + date_w + 8 + 3 + 8 + temp_w + 13 + 2
        dot_x = 225 - w / 2 + 1 + 13 + date_w + 8 + 1.5
        return "\n".join([
            pill(C, p(cy), s(w), s(h), stroke=border),
            text(date, p(dot_x - 1.5 - 8), p(cy), s(DATE_SIZE), align="END", width=s(date_w + 40),
                 spacing=DATE_SPACING),
            pill(p(dot_x), p(cy), s(3), s(3), fill="#80f2f0ea"),
            text(temp, p(dot_x + 1.5 + 8), p(cy), s(DATE_SIZE), color=AMBER, align="START",
                 width=s(temp_w + 40), spacing=DATE_SPACING)])

    def without():
        w = 13 + date_w + 13 + 2
        return "\n".join([pill(C, p(cy), s(w), s(h), stroke=border),
                          text(date, C, p(cy), s(DATE_SIZE), width=s(date_w + 40), spacing=DATE_SPACING)])
    return f"""<!-- Top pill: weekday, date · temperature -->
<Condition>
  <Expressions>
    <Expression name="hasWeather">[WEATHER.IS_AVAILABLE]</Expression>
  </Expressions>
  <Compare expression="hasWeather">
{indent(group("DateWeather", with_weather()), 4)}
  </Compare>
  <Default>
{indent(group("Date", without()), 4)}
  </Default>
</Condition>"""


def time():
    """Hours (ink) over minutes (lime), Unbounded 800 with the design's tight lines."""
    h = round(s(TIME_SIZE) * 1.3)

    def line(fmt, cy, color):
        return f"""<DigitalClock x="0" y="{round(p(cy) - h / 2)}" width="{SIZE}" height="{h}">
  <TimeText format="{fmt}" hourFormat="SYNC_TO_DEVICE" align="CENTER" x="0" y="0" width="{SIZE}" height="{h}">
    <Font family="unbounded_time" size="{s(TIME_SIZE):g}" color="{color}" />
  </TimeText>
</DigitalClock>"""
    return f"""<!-- Time: hours over minutes -->
{line("hh", HOURS_CY, INK)}
{line("mm", MINUTES_CY, LIME)}"""


def heart_pill():
    """Heart rate pill at the bottom, colored by zone (screen on only)."""
    h = 8 + BPM_SIZE + 8
    cy = PILL_BOTTOM - h / 2
    compares, exprs = [], []
    for zid, cond, bg, fg, heart, label, sample in ZONES:
        bw = text_width(sample, "unbounded_bold", BPM_SIZE)
        lw = text_width(label, "inter_semibold", PILL_LABEL_SIZE, LABEL_SPACING)
        w = 13 + PILL_HEART + 8 + bw + 8 + lw + 16
        x = 225 - w / 2 + 13
        hh = PILL_HEART * 0.89
        value = "--" if zid == "noHr" else template("%s", "round([HEART_RATE])")
        parts = [
            pill(C, p(cy), s(w), s(h), fill=bg),
            image("ic_heart", p(x), p(cy - hh / 2), s(PILL_HEART), s(hh), tint=heart),
            text(value, p(x + PILL_HEART + 8), p(cy), s(BPM_SIZE), font="unbounded_bold", color=fg,
                 align="START", width=s(bw + 30)),
            text(label, p(x + PILL_HEART + 8 + bw + 8), p(cy), s(PILL_LABEL_SIZE), color=fg,
                 align="START", width=s(lw + 30), spacing=LABEL_SPACING, extra=' alpha="204"')]
        exprs.append(f'    <Expression name="{zid}">{cond}</Expression>')
        compares.append(f"""  <Compare expression="{zid}">
{indent(group(zid, chr(10).join(parts)), 4)}
  </Compare>""")
    return f"""<!-- Heart rate pill, colored by zone (screen on only) -->
<Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="HeartRate">
  {AMBIENT_HIDE}
  <Condition>
    <Expressions>
{indent(chr(10).join(exprs), 2)}
    </Expressions>
{indent(chr(10).join(compares), 2)}
  </Condition>
</Group>"""


def tap_box(name, cx, cy, w, h):
    """Invisible box (design px) that opens MySteps' full-screen live pulse."""
    x, y, pw, ph = round(p(cx - w / 2)), round(p(cy - h / 2)), round(s(w)), round(s(h))
    return f"""<Group x="{x}" y="{y}" width="{pw}" height="{ph}" name="{name}">
  <Launch target="{HR_ACTIVITY}" />
  <PartDraw x="0" y="0" width="{pw}" height="{ph}">
    <Rectangle x="0" y="0" width="{pw}" height="{ph}">
      <Fill color="#00000000" />
    </Rectangle>
  </PartDraw>
</Group>"""


def taps():
    return f"""<!-- Tap on the time or the heart rate pill: big live pulse -->
{tap_box("TimeTap", 225, 225, 210, 2 * TIME_SIZE * TIME_LINE)}
{tap_box("HeartTap", 225, PILL_BOTTOM - 22, 200, 50)}"""


def strings():
    return """<?xml version="1.0" encoding="utf-8"?>
<!-- GENERATED by neoface/generate_watchface.py -->
<resources>
    <string name="watch_face_name">MySteps Neo</string>
    <string name="mysteps_slot_label">Inner ring (MySteps)</string>
    <string name="azm_slot_label">Outer ring (Zone Minutes)</string>
</resources>
"""


def watchface():
    scene = "\n\n".join([azm_slot(), steps_slot(), second_segment(), date_pill(), time(),
                         heart_pill(), taps()])
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!-- GENERATED by neoface/generate_watchface.py — edit that file, not this one. -->
<WatchFace width="{SIZE}" height="{SIZE}" clipShape="CIRCLE">
  <Metadata key="CLOCK_TYPE" value="DIGITAL" />
  <Metadata key="PREVIEW_TIME" value="10:08:32" />

  <Scene backgroundColor="#ff000000">
{indent(scene, 4)}
  </Scene>
</WatchFace>
"""


if __name__ == "__main__":
    OUT.write_text(watchface())
    (RES / "values/strings.xml").write_text(strings())
    print(f"wrote {OUT}")
