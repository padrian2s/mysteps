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

# Customize → Colors: (id, label, hours, minutes + steps, zone minutes); the first is the
# design's, the rest are the Fluid faces' themes (main -> minutes + steps, accent -> zone)
COLOR_OPTIONS = [
    ("neo", "Neo", INK, LIME, VIOLET),
    ("sand", "Sand & blue", INK, "#ffe9c98c", "#ff7d96ea"),
    ("mint", "Mint & pink", INK, "#ff6de18b", "#ffe3a6dd"),
    ("lilac", "Lilac Bliss", INK, "#ffc9b6ec", "#ff9b84d6"),
    ("teal", "Fitbit Teal", INK, "#ff39cccc", "#ffe2e2e2"),
    ("azm", "Zone Minutes", INK, "#fff8c33c", "#fff57c3a"),
    ("mono", "Silver", INK, "#ffe2e2e2", "#ff8f9bb3"),
    ("warty", "Warty Brown", INK, "#ffe8c9a1", "#ffc08850"),
    ("human", "Human", INK, "#fff2d2a9", "#fff57900"),
    ("earth", "Human Earth", INK, "#ffd8c3a5", "#ff9aae62"),
    ("spirit", "Human Spirit", INK, "#ffffd9a0", "#ffe95420"),
    ("gaia", "Gaia", INK, "#ffc9dca0", "#ff73a24a"),
    ("ambiance", "Ambiance", INK, "#ffdfdbd2", "#fff07746"),
    ("aubergine", "Aubergine", INK, "#fff6a37a", "#ffb37aa8"),
]
HOURS_C = "[CONFIGURATION.themeColor.0]"
MAIN_C = "[CONFIGURATION.themeColor.1]"    # minutes, steps ring and number
ZONE_C = "[CONFIGURATION.themeColor.2]"    # zone minutes segments and number

# Customize switches (default on) and lists (WFF has no sliders)
TOGGLES = [("showSteps", "Steps number"), ("showAzm", "Zone Minutes number"),
           ("showHr", "Heart rate"), ("showLabels", "Labels (MIN, PAȘI, zone)"),
           ("showSeconds", "Seconds segment")]
HR_SIZES = [("small", "Small", 0.85), ("normal", "Normal", 1.0), ("large", "Large", 1.15),
            ("xlarge", "Extra large", 1.3)]
# Zone minutes / steps numbers: (id, label, number px, label px)
SIDE_SIZES = [("small", "Small", 24, 12), ("normal", "Normal", 30, 13), ("large", "Large", 34, 15),
              ("xlarge", "Extra large", 38, 16)]
# Date and temperature: (id, label, px, with the weekday); Extra large drops the
# weekday so the pill still fits the top of the dial
DATE_SIZES = [("small", "Small", 18, True), ("normal", "Normal", 22, True), ("large", "Large", 26, True),
              ("xlarge", "Extra large", 31, False)]
# Ring thickness (design px): outer segments and the inner steps ring; the thickest of
# each still keeps the two rings apart (segments' inner edge 208, steps' outer 206)
SEG_WIDTHS = [("thin", "Thin", 5), ("normal", "Normal", 8), ("thick", "Thick", 11), ("xthick", "Extra thick", 12)]
STEPS_WIDTHS = [("thin", "Thin", 2), ("normal", "Normal", 4), ("thick", "Thick", 7), ("xthick", "Extra thick", 10)]
LISTS = [("hrSize", "Heart rate size", "normal", HR_SIZES),
         ("segWidth", "Zone Minutes segments thickness", "normal", SEG_WIDTHS),
         ("stepsWidth", "Steps ring thickness", "normal", STEPS_WIDTHS),
         ("sideSize", "Zone minutes / steps size", "normal", SIDE_SIZES),
         ("dateSize", "Date and temperature size", "normal", DATE_SIZES)]

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


def seg_half(w):
    """Half a segment's arc in degrees at width w: the round caps take w, gaps stay 5 px."""
    return (2 * math.pi * SEG_R / 60 - w - SEG_GAP) / 2 / SEG_R * 180 / math.pi


SEG_HALF = seg_half(SEG_W)
SEG_DIM = 46                     # opacity .18
STEPS_R, STEPS_W = 201, 4
STEPS_TRACK = 36                 # opacity .14

# Text sizes (design px), above the mock-up's (10-22 px read badly on the wrist):
# side numbers 22 -> 28, labels 10 -> 13, date pill 12 -> 15, bpm 21 -> 28
TIME_SIZE, TIME_LINE = 138, 0.82
HOURS_CY, MINUTES_CY = 225 - TIME_SIZE * TIME_LINE / 2, 225 + TIME_SIZE * TIME_LINE / 2
LABEL_SPACING = 0.14
SIDE_GAP = 5
# Columns centered between the inner ring (x 26) and the time's digits (x 123)
SIDE_LEFT_X, SIDE_RIGHT_X = 74, 450 - 74
DATE_SPACING, DATE_BOTTOM = 0.06, 110     # pill bottom, just above the hours
BPM_SIZE, PILL_LABEL_SIZE, PILL_HEART = 36, 14, 26    # asked bigger on the watch
PILL_BOTTOM = 398
PILL_WORD_MAX = 1.0      # the zone word only fits up to size Normal; above, the color says it


def date_height(size):
    """Date pill: Inter caps (0.73 em) + 8 px above and below + the 1 px border."""
    return size * 0.73 + 2 * 8 + 2


def side_centers(num, label):
    """Middles of the number and the label, the pair centered on the dial's middle."""
    total = num + SIDE_GAP + label
    return 225 - total / 2 + num / 2, 225 + total / 2 - label / 2


def pill_height(k):
    """Heart rate pill at size k: Unbounded caps (0.75 em) + 10 px above and below."""
    return BPM_SIZE * k * 0.75 + 2 * 10 * k


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


def switch(config_id, on, off=""):
    """Customize on/off switch (default on): on drawn when it is on, off otherwise."""
    opts = [("TRUE", on)] + ([("FALSE", off)] if off else [])
    body = "\n".join(f"""  <BooleanOption id="{oid}">
{indent(group(f"{config_id}_{oid}", xml), 4)}
  </BooleanOption>""" for oid, xml in opts)
    return f"""<BooleanConfiguration id="{config_id}">
{body}
</BooleanConfiguration>"""


def choice(config_id, options):
    """Customize list: options = [(option id, xml)], only the chosen one is drawn."""
    body = "\n".join(f"""  <ListOption id="{oid}">
{indent(group(f"{config_id}_{oid}", xml), 4)}
  </ListOption>""" for oid, xml in options)
    return f"""<ListConfiguration id="{config_id}">
{body}
</ListConfiguration>"""


RANGED = ("(clamp([COMPLICATION.RANGED_VALUE_VALUE], [COMPLICATION.RANGED_VALUE_MIN], "
          "[COMPLICATION.RANGED_VALUE_MAX]) - [COMPLICATION.RANGED_VALUE_MIN]) / "
          "([COMPLICATION.RANGED_VALUE_MAX] - [COMPLICATION.RANGED_VALUE_MIN])")
GOAL = "[COMPLICATION.GOAL_PROGRESS_VALUE] / [COMPLICATION.GOAL_PROGRESS_TARGET_VALUE]"


def side_column(cx, color, label, value, toggle_id):
    """Number over its small label, centered on x = cx (design px); without labels the
    number alone, centered on the dial's middle. Customize can hide the column."""
    def at(num, lab):
        def number(cy):
            return text(value, p(cx), p(cy), s(num), font="unbounded_bold", color=color, width=s(140))
        num_cy, lab_cy = side_centers(num, lab)
        with_label = "\n".join([
            number(num_cy),
            text(label, p(cx), p(lab_cy), s(lab), color=INK, width=s(110),
                 spacing=LABEL_SPACING, extra=' alpha="158"')])
        return switch("showLabels", with_label, number(225))
    return switch(toggle_id, choice("sideSize", [(oid, at(num, lab)) for oid, _, num, lab in SIDE_SIZES]))


def segments(fraction):
    """60 segments on the outer ring, centered on each second's mark; the first
    round(fraction * 60) lit (at least one once there is any), the rest dim."""
    lit = f"(({fraction}) &gt; 0 ? clamp(round(clamp({fraction}, 0, 1) * 60), 1, 60) : 0)" if fraction else "0"

    def at(w):
        half, out = seg_half(w), []
        for i in range(60):
            a = i * 6
            alpha = f'\n  <Transform target="alpha" value="{i} &lt; {lit} ? 255 : {SEG_DIM}" />' if fraction else ""
            dim = "" if fraction else f"\n  {AMBIENT_HIDE}"
            out.append(arc(s(SEG_R), s(w), ZONE_C, a - half, a + half,
                           alpha=255 if fraction else SEG_DIM, extra=alpha + dim))
        return "\n".join(out)
    return choice("segWidth", [(oid, at(w)) for oid, _, w in SEG_WIDTHS])


def azm_slot():
    """Outer ring + left column: Active Zone Minutes (Fitbit) by default. The watch
    clips a complication to its bounding shape: a full-screen oval."""
    def body(kind, fraction, value):
        parts = [segments(fraction), side_column(SIDE_LEFT_X, ZONE_C, "MIN", value, "showAzm")]
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
        return choice("stepsWidth", [(oid, ring_at(fraction, w)) for oid, _, w in STEPS_WIDTHS])

    def ring_at(fraction, w):
        track = arc(s(STEPS_R), s(w), MAIN_C, alpha=STEPS_TRACK, extra=f"\n  {AMBIENT_HIDE}")
        if not fraction:
            return track
        progress = arc(s(STEPS_R), s(w), MAIN_C, extra=(
            f'\n  <Transform target="alpha" value="({fraction}) &gt; 0 ? 255 : 0" />'),
            transform=f'\n    <Transform target="endAngle" value="clamp({fraction}, 0, 1) * 360" />')
        return track + "\n" + progress

    def body(kind, fraction, value):
        parts = [ring(fraction), side_column(SIDE_RIGHT_X, MAIN_C, "PAȘI", value, "showSteps")]
        return f"""<Complication type="{kind}">
{indent(group(kind, chr(10).join(parts)), 2)}
</Complication>"""
    label = template("%s", f"{met} ? subText([COMPLICATION.TEXT], 1, textLength([COMPLICATION.TEXT])) "
                           f": [COMPLICATION.TEXT]")
    o = round(C - s(STEPS_R + max(w for *_, w in STEPS_WIDTHS) / 2 + 1) - 1)
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
    seg = choice("segWidth", [(oid, arc(s(SEG_R), s(w), INK, -seg_half(w), seg_half(w)))
                              for oid, _, w in SEG_WIDTHS])
    return f"""<!-- Current second: white segment -->
{switch("showSeconds", f"""<Group x="0" y="0" width="{SIZE}" height="{SIZE}" pivotX="0.5" pivotY="0.5" name="Second">
  <Transform target="angle" value="[SECOND] * 6" />
  {AMBIENT_HIDE}
{indent(seg, 2)}
</Group>""")}"""


def date_pill():
    """Weekday, day and month · temperature (amber) in an outlined pill; without
    weather only the date. Size from Customize."""
    return f"""<!-- Top pill: weekday, date · temperature -->
{choice("dateSize", [(oid, date_pill_at(size, weekday)) for oid, _, size, weekday in DATE_SIZES])}"""


def date_pill_at(size, weekday):
    if weekday:
        date = template("%s %s %s", chain("[DAY_OF_WEEK]", DAYS), "[DAY]", chain("[MONTH]", MONTHS))
        date_w = text_width("MIE 28 NOV", "inter_semibold", size, DATE_SPACING)
    else:
        date = template("%s %s", "[DAY]", chain("[MONTH]", MONTHS))
        date_w = text_width("28 NOV", "inter_semibold", size, DATE_SPACING)
    temp = template("%s°", "[WEATHER.TEMPERATURE]")
    temp_w = text_width("25°", "inter_semibold", size, DATE_SPACING)
    h = date_height(size)
    cy = DATE_BOTTOM - h / 2
    border = ("#3df2f0ea", s(1))          # rgba(242,240,234,.24)

    def with_weather():
        w = 13 + date_w + 8 + 3 + 8 + temp_w + 13 + 2
        dot_x = 225 - w / 2 + 1 + 13 + date_w + 8 + 1.5
        return "\n".join([
            pill(C, p(cy), s(w), s(h), stroke=border),
            text(date, p(dot_x - 1.5 - 8), p(cy), s(size), align="END", width=s(date_w + 40),
                 spacing=DATE_SPACING),
            pill(p(dot_x), p(cy), s(3), s(3), fill="#80f2f0ea"),
            text(temp, p(dot_x + 1.5 + 8), p(cy), s(size), color=AMBER, align="START",
                 width=s(temp_w + 40), spacing=DATE_SPACING)])

    def without():
        w = 13 + date_w + 13 + 2
        return "\n".join([pill(C, p(cy), s(w), s(h), stroke=border),
                          text(date, C, p(cy), s(size), width=s(date_w + 40), spacing=DATE_SPACING)])
    return f"""<Condition>
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
{line("hh", HOURS_CY, HOURS_C)}
{line("mm", MINUTES_CY, MAIN_C)}"""


def heart_pill():
    """Heart rate pill at the bottom, colored by zone (screen on only); size and the
    zone word from Customize."""
    return f"""<!-- Heart rate pill, colored by zone (screen on only) -->
<Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="HeartRate">
  {AMBIENT_HIDE}
{indent(switch("showHr", choice("hrSize", [
        (oid, switch("showLabels", heart_pill_at(k, True), heart_pill_at(k, False)))
        for oid, _, k in HR_SIZES])), 2)}
</Group>"""


def heart_pill_at(k, labels):
    """The pill at size k (bottom edge fixed), zone word or not, one per zone."""
    bpm, lab, heart_w = BPM_SIZE * k, PILL_LABEL_SIZE * k, PILL_HEART * k
    h = pill_height(k)
    labels = labels and k <= PILL_WORD_MAX
    cy = PILL_BOTTOM - h / 2
    compares, exprs = [], []
    for zid, cond, bg, fg, heart, label, sample in ZONES:
        bw = text_width(sample, "unbounded_bold", bpm)
        lw = text_width(label, "inter_semibold", lab, LABEL_SPACING) if labels else 0
        w = 11 * k + heart_w + 8 * k + bw + (8 * k + lw if labels else 0) + 13 * k
        x = 225 - w / 2 + 11 * k
        hh = heart_w * 0.89
        value = "--" if zid == "noHr" else template("%s", "round([HEART_RATE])")
        parts = [
            pill(C, p(cy), s(w), s(h), fill=bg),
            image("ic_heart", p(x), p(cy - hh / 2), s(heart_w), s(hh), tint=heart),
            text(value, p(x + heart_w + 8 * k), p(cy), s(bpm), font="unbounded_bold", color=fg,
                 align="START", width=s(bw + 30))]
        if labels:
            parts.append(text(label, p(x + heart_w + 8 * k + bw + 8 * k), p(cy), s(lab), color=fg,
                              align="START", width=s(lw + 30), spacing=LABEL_SPACING, extra=' alpha="204"'))
        exprs.append(f'    <Expression name="{zid}">{cond}</Expression>')
        compares.append(f"""  <Compare expression="{zid}">
{indent(group(zid, chr(10).join(parts)), 4)}
  </Compare>""")
    return f"""<Condition>
  <Expressions>
{chr(10).join(exprs)}
  </Expressions>
{chr(10).join(compares)}
</Condition>"""


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
{tap_box("HeartTap", 225, PILL_BOTTOM - 30, 240, 64)}"""


def strings():
    colors = "\n".join(f'    <string name="colors_{oid}">{label.replace("&", "&amp;")}</string>'
                       for oid, label, *_ in COLOR_OPTIONS)
    toggles = "\n".join(f'    <string name="{tid}_label">{label}</string>' for tid, label in TOGGLES)
    lists = "\n".join(
        f'    <string name="{lid}_label">{label}</string>\n' + "\n".join(
            f'    <string name="{lid}_{o[0]}">{o[1]}</string>' for o in opts)
        for lid, label, _, opts in LISTS)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!-- GENERATED by neoface/generate_watchface.py -->
<resources>
    <string name="watch_face_name">MySteps Neo</string>
    <string name="mysteps_slot_label">Inner ring (MySteps)</string>
    <string name="azm_slot_label">Outer ring (Zone Minutes)</string>
    <string name="colors_label">Colors</string>
{toggles}
{lists}
{colors}
</resources>
"""


def user_configurations():
    colors = "\n".join(
        f'<ColorOption id="{oid}" displayName="colors_{oid}" screenReaderText="colors_{oid}" colors="{a} {b} {c}" />'
        for oid, _, a, b, c in COLOR_OPTIONS)
    lists = "\n".join(
        f'<ListConfiguration id="{lid}" displayName="{lid}_label" screenReaderText="{lid}_label" defaultValue="{default}">\n'
        + "\n".join(f'  <ListOption id="{o[0]}" displayName="{lid}_{o[0]}" screenReaderText="{lid}_{o[0]}" />' for o in opts)
        + "\n</ListConfiguration>"
        for lid, _, default, opts in LISTS)
    toggles = "\n".join(
        f'<BooleanConfiguration id="{tid}" displayName="{tid}_label" screenReaderText="{tid}_label" defaultValue="TRUE" />'
        for tid, _ in TOGGLES)
    return f"""<UserConfigurations>
  <ColorConfiguration id="themeColor" displayName="colors_label" defaultValue="{COLOR_OPTIONS[0][0]}">
{indent(colors, 4)}
  </ColorConfiguration>
{indent(lists, 2)}
{indent(toggles, 2)}
</UserConfigurations>"""


def watchface():
    scene = "\n\n".join([azm_slot(), steps_slot(), second_segment(), date_pill(), time(),
                         heart_pill(), taps()])
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!-- GENERATED by neoface/generate_watchface.py — edit that file, not this one. -->
<WatchFace width="{SIZE}" height="{SIZE}" clipShape="CIRCLE">
  <Metadata key="CLOCK_TYPE" value="DIGITAL" />
  <Metadata key="PREVIEW_TIME" value="10:08:32" />

{indent(user_configurations(), 2)}

  <Scene backgroundColor="#ff000000">
{indent(scene, 4)}
  </Scene>
</WatchFace>
"""


if __name__ == "__main__":
    OUT.write_text(watchface())
    (RES / "values/strings.xml").write_text(strings())
    print(f"wrote {OUT}")
