#!/usr/bin/env python3
"""Generates src/main/res/raw/watchface.xml for the Fluid v3 watch face.

Edit this file, not the XML:

    python3 fluid3face/generate_watchface.py

The layout follows the "Cadran Fluid v3" design (450 px HTML mock-up, Jost), scaled to
the Pixel Watch 3's 456 px: two concentric rings that fill clockwise from 12 o'clock
(Active Zone Minutes outside, MySteps steps this hour inside) with black ticks on the
filled part, a thin inner ring carrying the seconds dot, short dauphine hands near the
rim, the date on top, a big extra-light time with the heart rate between hours and
minutes (♥, bpm and three zone pills colored by zone), zone minutes and steps below
and the temperature at the bottom. Not offloadable, so raising the wrist wakes Android
and MySteps refreshes.
"""
import math
from pathlib import Path
from fontTools.ttLib import TTFont
from PIL import Image

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


# Customize → Colors: (id, label, main, accent); the first is the design's
COLOR_OPTIONS = [
    ("sand", "Sand & blue", "#ffe9c98c", "#ff7d96ea"),
    ("mint", "Mint & pink", "#ff6de18b", "#ffe3a6dd"),
    ("lilac", "Lilac Bliss", "#ffc9b6ec", "#ff9b84d6"),
    ("teal", "Fitbit Teal", "#ff39cccc", "#ffe2e2e2"),
    ("azm", "Zone Minutes", "#fff8c33c", "#fff57c3a"),
    ("mono", "Silver", "#ffe2e2e2", "#ff8f9bb3"),
    ("warty", "Warty Brown", "#ffe8c9a1", "#ffc08850"),
    ("human", "Human", "#fff2d2a9", "#fff57900"),
    ("earth", "Human Earth", "#ffd8c3a5", "#ff9aae62"),
    ("spirit", "Human Spirit", "#ffffd9a0", "#ffe95420"),
    ("gaia", "Gaia", "#ffc9dca0", "#ff73a24a"),
    ("ambiance", "Ambiance", "#ffdfdbd2", "#fff07746"),
    ("aubergine", "Aubergine", "#fff6a37a", "#ffb37aa8"),
]
MAIN = "[CONFIGURATION.themeColor.0]"    # time, date, steps ring and number, seconds dot
ACCENT = "[CONFIGURATION.themeColor.1]"  # zone minutes ring and number
ORANGE = "#ffe39a5a"                     # temperature

# Heart rate zones as in the design: rest < 100, active 100-129, cardio >= 130
HR_ACTIVE, HR_CARDIO = 100, 130
ZONES = [("hrRest", "#ff8f9bb3"), ("hrActive", "#ffe39a5a"), ("hrCardio", "#ffe5493f")]
ZONE_EXPR = {"hrRest": f"[HEART_RATE] &lt; {HR_ACTIVE}",
             "hrActive": f"[HEART_RATE] &gt;= {HR_ACTIVE} &amp;&amp; [HEART_RATE] &lt; {HR_CARDIO}",
             "hrCardio": f"[HEART_RATE] &gt;= {HR_CARDIO}"}

# Rings (design px, like the mock-up's SVG): fixed mid radii, so every width keeps
# them apart and the ticks (cut across the widest band) never touch the other ring
RING_AZM_R, RING_STEPS_R = 217.5, 205.5
SECONDS_R = 198
# Black ticks on the filled part: steps one per 50 (max 30), Zone Minutes one per minute
# (max 45). A met MySteps hour carries no goal (max 1): ticks of the 300-step goal (6)
STEP_GOAL_TICKS = 6

# Customize lists (WFF has no sliders): (id, label, default, [(option id, label, value)])
RING_WIDTHS = [("thin", "Thin", 3), ("normal", "Normal", 6), ("thick", "Thick", 9)]
BAND = max(w for _, _, w in RING_WIDTHS)
GAPS = [("none", "None", 0), ("small", "Small", 3.5), ("medium", "Medium", 7), ("large", "Large", 10)]
HAND_SIZES = [("small", "Small"), ("normal", "Normal"), ("large", "Large"), ("hidden", "Hidden")]
TIME_FONTS = [("light", "Light", "jost_light"), ("regular", "Regular", "jost_regular"),
              ("bold", "Bold", "jost_time"), ("strong", "Strong", "jost_time_strong"),
              ("vstrong", "Very strong", "jost_time_vstrong"), ("ultra", "Ultra bold", "jost_time_ultra")]
TIME_SIZES = [("small", "Small", 96), ("normal", "Normal", 108), ("large", "Large", 118)]
TEXT_SIZES = [("small", "Small", 0.85), ("normal", "Normal", 1.0), ("large", "Large", 1.15)]
# Heart rate position: (id, label, layout, x, y) in design px; x "hh" / "mm" = above or
# below the hour / minute digits. "middle" is the design's: vertical between hh and mm.
# Elsewhere it is hh:mm (colon instead of the gap) and the block is a ♥ bpm row with
# the zone pills under it ("v" = small vertical stack, between the bottom numbers).
HR_POSITIONS = [("middle", "Between hour and minutes", "mid", 225, None),
                ("aboveDate", "Above the date", "h", 225, 62),
                ("belowDate", "Between date and time", "h", 225, 145),
                ("aboveHour", "Above the hour (left)", "h", "hh", 145),
                ("aboveMin", "Above the minutes (right)", "h", "mm", 145),
                ("belowHour", "Below the hour (left)", "h", "hh", 280),
                ("belowMin", "Below the minutes (right)", "h", "mm", 280),
                ("bottomMid", "Between the bottom numbers", "v", 225, 333),
                ("aboveTemp", "Above the temperature", "h", 225, 350)]
DATE_SHIFT = {"aboveDate": 34}     # date moves down under the heart rate
TEMP_SHIFT = {"aboveTemp": 14}     # temperature moves down under the heart rate
LISTS = [("hrPos", "Heart rate position", "middle", HR_POSITIONS),
         ("ringWidth", "Ring thickness", "normal", RING_WIDTHS),
         ("ringGaps", "Ring gaps", "medium", GAPS),
         ("handSize", "Hands", "normal", HAND_SIZES),
         ("timeFont", "Time weight", "bold", TIME_FONTS),
         ("timeSize", "Time size", "normal", TIME_SIZES),
         ("textSize", "Date, temperature, numbers", "normal", TEXT_SIZES)]

# Text sizes (design px), well above the mock-up's (12-30 px read badly on the wrist):
# day 30 -> 44, month 12 -> 20, temperature 15 -> 32, zone minutes / steps 30 -> 44
DATE_TOP = 52
DAY_SIZE, MONTH_SIZE, TEMP_SIZE = 44, 20, 32

MONTHS = ["IAN", "FEB", "MAR", "APR", "MAI", "IUN", "IUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
AMBIENT_HIDE = '<Variant mode="AMBIENT" target="alpha" value="0" />'
HR_ACTIVITY = "com.adrianp.mysteps/com.adrianp.mysteps.presentation.HeartRateActivity"

FONT_FILES = {n: TTFont(RES / "font" / f"{n}.ttf")
              for n in ("jost_extralight", "jost_light", "jost_regular", "jost_time",
                                   "jost_time_strong", "jost_time_vstrong", "jost_time_ultra")}
LINE = 1.445      # Jost's normal line height (hhea 1070 + 375 per 1000); its line box
                  # is centered on the caps (cap middle 350 vs box middle 347.5)

TOGGLES = [("showSteps", "Steps number"), ("showAzm", "Zone Minutes number"),
           ("showHr", "Heart rate"), ("showSeconds", "Seconds dot")]


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


def text(content, cx, cy, size, font="jost_light", color=MAIN, width=None, extra="",
         spacing=0.0, align="CENTER", inner=""):
    """Single-line text whose line box (= cap) middle sits on (cx, cy), watch px.
    align=START puts the left edge at cx, END the right edge."""
    w = round(width or SIZE)
    h = round(size * 1.6)
    x = {"CENTER": cx - w / 2, "START": cx, "END": cx - w}[align]
    ls = f' letterSpacing="{spacing:g}"' if spacing else ""
    return f"""<PartText x="{round(x)}" y="{round(cy - h / 2)}" width="{w}" height="{h}"{extra}>{inner}
  <Text align="{align}">
    <Font family="{font}" size="{size:g}" color="{color}"{ls}>{content}</Font>
  </Text>
</PartText>"""


def template(expr, fmt="%s"):
    return f'<Template>{fmt}<Parameter expression="{expr}" /></Template>'


def image(resource, x, y, w, h, extra="", tint=None, inner=""):
    t = f' tintColor="{tint}"' if tint else ""
    return f"""<PartImage x="{round(x)}" y="{round(y)}" width="{round(w)}" height="{round(h)}"{t}{extra}>{inner}
  <Image resource="{resource}" />
</PartImage>"""


def arc(r, stroke, color, fraction=None, alpha=255, extra=""):
    """Full-screen arc from 12 o'clock clockwise, on mid-radius r (watch px);
    fraction = expression 0..1 of a full turn (None = whole circle)."""
    a = f' alpha="{alpha}"' if alpha != 255 else ""
    transform = ""
    if fraction is not None:
        # A zero-length arc would still draw a round cap: hide it at 0
        a = ""
        extra = f'\n  <Transform target="alpha" value="({fraction}) &gt; 0 ? {alpha} : 0" />' + extra
        transform = f'\n    <Transform target="endAngle" value="clamp({fraction}, 0, 1) * 360" />'
    return f"""<PartDraw x="0" y="0" width="{SIZE}" height="{SIZE}"{a}>{extra}
  <Arc centerX="{C:g}" centerY="{C:g}" width="{2 * r:g}" height="{2 * r:g}" startAngle="0" endAngle="360">{transform}
    <Stroke color="{color}" thickness="{stroke:g}" cap="ROUND" />
  </Arc>
</PartDraw>"""


def glowing_arc(r, stroke, color, fraction, glow):
    """Progress arc with a soft halo (the design's drop-shadow 0 0 3px), dropped in always-on."""
    halo = [arc(r, stroke + glow * k, color, fraction, alpha=a, extra=f"\n  {AMBIENT_HIDE}")
            for k, a in ((1.6, 22), (0.8, 45))]
    return "\n".join(halo + [arc(r, stroke, color, fraction)])


def disc(cx, cy, d, color, extra="", inner=""):
    x, y = math.floor(cx - d / 2), math.floor(cy - d / 2)
    box = math.ceil(max(cx + d / 2 - x, cy + d / 2 - y))
    return f"""<PartDraw x="{x}" y="{y}" width="{box}" height="{box}"{extra}>{inner}
  <Ellipse x="{cx - d / 2 - x:g}" y="{cy - d / 2 - y:g}" width="{d:g}" height="{d:g}">
    <Fill color="{color}" />
  </Ellipse>
</PartDraw>"""


def rect(x, y, w, h, color, extra="", inner=""):
    return f"""<PartDraw x="{round(x)}" y="{round(y)}" width="{math.ceil(w)}" height="{math.ceil(h)}"{extra}>{inner}
  <Rectangle x="0" y="0" width="{math.ceil(w)}" height="{math.ceil(h)}">
    <Fill color="{color}" />
  </Rectangle>
</PartDraw>"""


def toggle(config_id, xml):
    """Customize on/off switch (default on): xml drawn only when the switch is on."""
    return f"""<BooleanConfiguration id="{config_id}">
  <BooleanOption id="TRUE">
    <Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="{config_id}">
{indent(xml, 6)}
    </Group>
  </BooleanOption>
</BooleanConfiguration>"""


def choice(config_id, options):
    """Customize list: options = [(option id, xml)], only the chosen one is drawn."""
    opts = "\n".join(f"""  <ListOption id="{oid}">
    <Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="{config_id}_{oid}">
{indent(xml, 6)}
    </Group>
  </ListOption>""" for oid, xml in options)
    return f"""<ListConfiguration id="{config_id}">
{opts}
</ListConfiguration>"""


def zone_switch(make):
    """Condition drawing make(color) in the current heart rate zone's color; nothing
    without a reading."""
    compares = "".join(f"""
  <Compare expression="{name}">
{indent(make(color), 4)}
  </Compare>""" for name, color in ZONES)
    exprs = "\n".join(f'    <Expression name="{n}">[HEART_RATE] &gt; 0 &amp;&amp; {ZONE_EXPR[n]}</Expression>'
                      for n, _ in ZONES)
    return f"""<Condition>
  <Expressions>
{exprs}
  </Expressions>{compares}
</Condition>"""


RANGED = ("(clamp([COMPLICATION.RANGED_VALUE_VALUE], [COMPLICATION.RANGED_VALUE_MIN], "
          "[COMPLICATION.RANGED_VALUE_MAX]) - [COMPLICATION.RANGED_VALUE_MIN]) / "
          "([COMPLICATION.RANGED_VALUE_MAX] - [COMPLICATION.RANGED_VALUE_MIN])")
GOAL = "[COMPLICATION.GOAL_PROGRESS_VALUE] / [COMPLICATION.GOAL_PROGRESS_TARGET_VALUE]"

# ---- Time: hh [♥ / bpm / zone pills] mm ---------------------------------------------
TIME_SIZE = 108
TIME_CY = (450 - 20) / 2                    # padding-bottom 20
HEART_SIZE, BPM_SIZE = 26, 54      # the design's 20 / 40, bigger (asked on the watch)
PILL_W, PILL_H, PILL_GAP = 14, 2, 4
MID_H = HEART_SIZE + 2 + BPM_SIZE + 2 + 5 + PILL_H
MID_TOP = TIME_CY - MID_H / 2
HEART_CY = MID_TOP + HEART_SIZE / 2
BPM_CY = MID_TOP + HEART_SIZE + 2 + BPM_SIZE / 2
PILLS_CY = MID_TOP + HEART_SIZE + 2 + BPM_SIZE + 2 + 5 + PILL_H / 2
MID_W = max(text_width("89", "jost_regular", BPM_SIZE), 3 * PILL_W + 2 * PILL_GAP) + 2 * 8
DIGITS_W = text_width("00", "jost_time", TIME_SIZE)    # tracking is in the advances
TIME_LEFT = 225 - (2 * DIGITS_W + MID_W) / 2

# ---- Bottom row: zone minutes and steps, 150 px apart --------------------------------
VALUE_SIZE = 44
VALUE_CY = 333


def value_cols():
    w1, w2 = text_width("77", "jost_regular", VALUE_SIZE), text_width("180", "jost_regular", VALUE_SIZE)
    left = 225 - (w1 + 150 + w2) / 2
    return left + w1 / 2, left + w1 + 150 + w2 / 2


def ring_ticks(r, gap, value, maxv, unit, cap, goal_met=None, fallback=None):
    """Black radial cuts gap px wide on the filled part of a ring (design px r), across
    the widest band, one per unit of the goal maxv, at most cap (beyond that a tick is
    worth maxv / cap)."""
    n = f"clamp(round({maxv} / {unit}), 1, {cap})"
    done = f"({value} * {n} / {maxv})"      # filled length in ticks
    if goal_met:
        n = f"({goal_met} ? {fallback} : {n})"
        done = f"({goal_met} ? {fallback} : {done})"
    r0, r1 = (r - BAND / 2 - 1) * K, (r + BAND / 2 + 1) * K
    ticks = []
    for i in range(1, cap):                 # none at 12 o'clock, where the ring starts
        ticks.append(f"""<Group x="0" y="0" width="{SIZE}" height="{SIZE}" pivotX="0.5" pivotY="0.5" name="Tick{i}">
  <Transform target="angle" value="{i} * 360 / {n}" />
  <Transform target="alpha" value="{i} &lt; {n} &amp;&amp; {i} &lt; {done} ? 255 : 0" />
  <PartDraw x="0" y="0" width="{SIZE}" height="{SIZE}">
    <Line startX="{C:g}" startY="{C - r0:.1f}" endX="{C:g}" endY="{C - r1:.1f}">
      <Stroke color="#ff000000" thickness="{gap * K:.2f}" />
    </Line>
  </PartDraw>
</Group>""")
    return "\n".join(ticks)


def ring_slot(slot_id, name, provider, r, color, track_alpha, cx, toggle_id, unit, cap,
              comment, area, full_at_max_one=False):
    """Complication slot drawing its ring (track, glowing progress, ticks) and its number.
    The watch clips a complication to its bounding shape, so area is a centered oval of
    that radius (watch px): the outer slot covers the screen, the inner one the disc
    inside, so taps on the outer band go to the outer ring's provider."""
    def body(kind, fraction):
        def ring(w):
            track = arc(s(r), s(w), color, alpha=track_alpha, extra=f"\n  {AMBIENT_HIDE}")
            return track + "\n" + glowing_arc(s(r), s(w), color, fraction, 3) if fraction else track
        if fraction and full_at_max_one:
            # MySteps sends value 0 of max 1 once the hour's goal is met: full ring then
            met = "[COMPLICATION.RANGED_VALUE_MAX] == 1"
            if kind == "RANGED_VALUE":
                fraction = f"({met} ? 1 : {fraction})"
        parts = [choice("ringWidth", [(oid, ring(w)) for oid, _, w in RING_WIDTHS])]
        if fraction:
            met = "[COMPLICATION.RANGED_VALUE_MAX] == 1" if full_at_max_one else None
            value, maxv = (("[COMPLICATION.RANGED_VALUE_VALUE]", "[COMPLICATION.RANGED_VALUE_MAX]")
                           if kind == "RANGED_VALUE" else
                           ("[COMPLICATION.GOAL_PROGRESS_VALUE]", "[COMPLICATION.GOAL_PROGRESS_TARGET_VALUE]"))
            parts.append(choice("ringGaps", [
                (oid, ring_ticks(r, gap, value, maxv, unit, cap,
                                 met if kind == "RANGED_VALUE" else None, STEP_GOAL_TICKS) if gap else "")
                for oid, _, gap in GAPS]))
        if kind == "EMPTY":
            label = "--"
        else:
            label = "[COMPLICATION.TEXT]"
            if full_at_max_one and kind == "RANGED_VALUE":
                # Goal met: MySteps sends "❤N/M"; the full ring already says it, drop the ❤
                label = ("[COMPLICATION.RANGED_VALUE_MAX] == 1 ? subText([COMPLICATION.TEXT], 1, "
                         "textLength([COMPLICATION.TEXT])) : [COMPLICATION.TEXT]")
            label = template(label)
        number = choice("textSize", [
            (oid, text(label, p(cx), p(VALUE_CY), s(VALUE_SIZE * k), font="jost_regular", color=color,
                       width=s(VALUE_SIZE * k * 3.5)))
            for oid, _, k in TEXT_SIZES])
        parts.append(f"""<Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="Number">
{indent(toggle(toggle_id, number), 2)}
</Group>""")
        return f"""<Complication type="{kind}">
  <Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="{kind}">
{indent(chr(10).join(parts), 4)}
  </Group>
</Complication>"""

    o = round(C - area)
    return f"""<!-- {comment} -->
<ComplicationSlot x="0" y="0" width="{SIZE}" height="{SIZE}" slotId="{slot_id}"
    displayName="{name}" supportedTypes="RANGED_VALUE GOAL_PROGRESS SHORT_TEXT EMPTY">
  <DefaultProviderPolicy
      primaryProvider="{provider}"
      primaryProviderType="RANGED_VALUE"
      defaultSystemProvider="EMPTY"
      defaultSystemProviderType="EMPTY" />
  <BoundingOval x="{o}" y="{o}" width="{SIZE - 2 * o}" height="{SIZE - 2 * o}" />
{indent(body("RANGED_VALUE", RANGED), 2)}
{indent(body("GOAL_PROGRESS", GOAL), 2)}
{indent(body("SHORT_TEXT", None), 2)}
{indent(body("EMPTY", None), 2)}
</ComplicationSlot>"""


def seconds_ring():
    """Thin inner ring with the seconds dot on it (dot hidden in always-on)."""
    r = s(SECONDS_R)
    theta = "rad([SECOND] * 6)"
    d, box = s(6), round(s(6) + 8)
    dot = f"""<Group x="0" y="0" width="{box:g}" height="{box:g}" name="SecondsDot">
  <Transform target="x" value="{C:g} + {r} * sin({theta}) - {box / 2:g}" />
  <Transform target="y" value="{C:g} - {r} * cos({theta}) - {box / 2:g}" />
  {AMBIENT_HIDE}
{indent(disc(box / 2, box / 2, box, MAIN, extra=' alpha="40"'), 2)}
{indent(disc(box / 2, box / 2, d + 3, MAIN, extra=' alpha="90"'), 2)}
{indent(disc(box / 2, box / 2, d, MAIN), 2)}
</Group>"""
    return f"""<!-- Thin inner ring and the seconds dot -->
{toggle("showSeconds", arc(r, 1, MAIN, alpha=31) + chr(10) + dot)}"""


def hands():
    """Short dauphine hands near the rim (images from tools/build_assets.py, pivot at the
    image's bottom middle = the dial center)."""
    def hand(tag, res):
        w, h = Image.open(RES / "drawable" / f"{res}.png").size
        x = math.floor(C - w / 2)     # whole px; the pivot stays on the dial center
        return (f'<{tag} resource="{res}" x="{x}" y="{round(C - h)}" width="{w}" height="{h}" '
                f'pivotX="{(C - x) / w:.4f}" pivotY="1" />')
    def clock(size):
        return f"""<AnalogClock x="0" y="0" width="{SIZE}" height="{SIZE}">
  {hand("HourHand", f"hand_hour_{size}")}
  {hand("MinuteHand", f"hand_minute_{size}")}
</AnalogClock>"""
    return f"""<!-- Dauphine hands, only near the rim -->
{choice("handSize", [(oid, "" if oid == "hidden" else clock(oid)) for oid, _ in HAND_SIZES])}"""


def date():
    month = template(chain("[MONTH]", [m + "." for m in MONTHS]))

    def at(k, top):
        day, mon = DAY_SIZE * k, MONTH_SIZE * k
        return f"""{text(template("[DAY]"), C, p(top + day / 2), s(day), font="jost_regular", width=s(day * 3))}
{text(month, C, p(top + day + 2 + mon * LINE / 2), s(mon), font="jost_regular",
      width=s(mon * 8), spacing=0.2, extra=' alpha="170"')}"""

    def sizes(top):
        return choice("textSize", [(oid, at(k, top)) for oid, _, k in TEXT_SIZES])
    return f"""<!-- Date: day of the month, month below (lower when the heart rate sits above) -->
{choice("hrPos", [(pid, sizes(DATE_TOP + DATE_SHIFT.get(pid, 0))) for pid, *_ in HR_POSITIONS])}"""


def time():
    """hh and mm (tabular digits) around the heart rate; weight and size from Customize
    (default bold 108 px; the design had extra-light). With the heart rate elsewhere the
    hours and minutes touch."""
    def fonts(gap):
        return choice("timeFont", [(fid, choice("timeSize", [(sid, time_pair(font, size, gap))
                                                             for sid, _, size in TIME_SIZES]))
                                   for fid, _, font in TIME_FONTS])
    return f"""<!-- Time -->
{choice("hrPos", [(pid, fonts(MID_W if pid == "middle" else 0)) for pid, *_ in HR_POSITIONS])}"""


def colon_rise(font):
    """How far (per px of font size) Jost's colon sits below the digits' middle: it is
    centered on the x-height, the digits on the caps (350)."""
    from fontTools.pens.boundsPen import BoundsPen
    gs = FONT_FILES[font].getGlyphSet()
    pen = BoundsPen(gs)
    gs["colon"].draw(pen)
    return (350 - (pen.bounds[1] + pen.bounds[3]) / 2) / 1000


def time_pair(font, size, gap):
    """hh and mm gap px apart; no gap = the heart rate is elsewhere: hh:mm with a colon
    raised to the digits' middle."""
    digits = text_width("00", font, size)
    colon = ""
    if not gap:
        gap = text_width(":", font, size)
        colon = "\n" + text(":", C, p(TIME_CY - colon_rise(font) * size), s(size), font=font,
                            width=s(gap + 20))
    left = 225 - (2 * digits + gap) / 2
    h = round(s(size) * 1.6)
    w = round(s(digits + 20))
    cy = p(TIME_CY)

    def clock(fmt, x_edge, align):
        x = x_edge if align == "START" else x_edge - w
        return f"""<DigitalClock x="{round(x)}" y="{round(cy - h / 2)}" width="{w}" height="{h}">
  <TimeText format="{fmt}" hourFormat="SYNC_TO_DEVICE" align="{align}" x="0" y="0" width="{w}" height="{h}">
    <Font family="{font}" size="{s(size):g}" color="{MAIN}" />
  </TimeText>
</DigitalClock>"""
    return f"""{clock("hh", p(left + digits), "END")}
{clock("mm", p(left + digits + gap), "START")}{colon}"""


# ---- Heart rate block elsewhere: sizes (design px) at text size Normal ---------------
HR_ROW_HEART, HR_ROW_BPM = 22, 36    # ♥ bpm row
HR_CAP = 0.35                         # half of Jost's cap height, per px of font size


def hr_x(x):
    """Block center x (design px): a number, or the middle of the hh / mm digits."""
    half = (DIGITS_W + text_width(":", "jost_time", TIME_SIZE)) / 2
    return {"hh": 225 - half, "mm": 225 + half}.get(x, x)


def pills(color, cx, cy):
    """The three zone pills centered on (cx, cy) design px, the current zone lit."""
    x0 = cx - (3 * PILL_W + 2 * PILL_GAP) / 2
    out = []
    for i, (_, zc) in enumerate(ZONES):
        x = p(x0 + i * (PILL_W + PILL_GAP))
        lit = zc == color
        if lit:     # box-shadow 0 0 6px: a faint wider bar behind
            out.append(rect(x - 2, p(cy) - s(PILL_H) / 2 - 2, s(PILL_W) + 4, s(PILL_H) + 4, zc,
                            extra=' alpha="60"'))
        out.append(rect(x, p(cy) - s(PILL_H) / 2, s(PILL_W), s(PILL_H), zc,
                        extra="" if lit else ' alpha="64"'))
    return "\n".join(out)


def heart_icon(color, cx, cy, size):
    hs = s(size * 0.83)
    return image("ic_heart", p(cx) - hs / 2, p(cy) - hs * 0.89 / 2, hs, hs * 0.89, tint=color)


BPM = template("round([HEART_RATE])")


def hr_variants(draw):
    """draw(color, value) in the zone's color, or (rest color, "--") without a reading."""
    return zone_switch(lambda c: draw(c, BPM)) + f"""
<Condition>
  <Expressions>
    <Expression name="noHr">[HEART_RATE] &lt;= 0</Expression>
  </Expressions>
  <Compare expression="noHr">
{indent(draw(ZONES[0][1], "--"), 4)}
  </Compare>
</Condition>"""


def hr_middle():
    """The design's: ♥, bpm and pills stacked between hours and minutes."""
    def draw(c, value):
        return "\n".join([heart_icon(c, 225, HEART_CY, HEART_SIZE),
                          text(value, C, p(BPM_CY), s(BPM_SIZE), font="jost_regular", color=c,
                               width=s(BPM_SIZE * 3)),
                          pills(c, 225, PILLS_CY)])
    return hr_variants(draw)


def hr_row(cx, cy, k):
    """♥ bpm on one row centered on (cx, cy) (centered for a 2-digit bpm, a third digit
    grows to the right), pills under it."""
    hsz, b = HR_ROW_HEART * k, HR_ROW_BPM * k
    hw = hsz * 0.83
    left = cx - (hw + 5 * k + text_width("75", "jost_regular", b)) / 2

    def draw(c, value):
        return "\n".join([heart_icon(c, left + hw / 2, cy, hsz),
                          text(value, p(left + hw + 5 * k), p(cy), s(b), font="jost_regular", color=c,
                               align="START", width=s(b * 3)),
                          pills(c, cx, cy + b * HR_CAP + 6)])
    return hr_variants(draw)


def hr_stack(cx, cy, k):
    """Small ♥ / bpm / pills stack, bpm centered on (cx, cy)."""
    hsz, b = HR_ROW_HEART * k * 0.9, HR_ROW_BPM * k

    def draw(c, value):
        return "\n".join([heart_icon(c, cx, cy - b * HR_CAP - 4 - hsz * 0.37, hsz),
                          text(value, p(cx), p(cy), s(b), font="jost_regular", color=c, width=s(b * 3)),
                          pills(c, cx, cy + b * HR_CAP + 6)])
    return hr_variants(draw)


def heart_rate():
    """♥, bpm and the three zone pills, colored by zone, where Customize → Heart rate
    position puts them. Hidden in always-on (the bpm only updates while the screen is on)."""
    def at(layout, x, y):
        if layout == "mid":
            return hr_middle()
        make = hr_row if layout == "h" else hr_stack
        return choice("textSize", [(oid, make(hr_x(x), y, k)) for oid, _, k in TEXT_SIZES])
    return f"""<!-- Heart rate, colored by zone (screen on only) -->
<Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="HeartRate">
  {AMBIENT_HIDE}
{indent(toggle("showHr", choice("hrPos", [(pid, at(lay, x, y)) for pid, _, lay, x, y in HR_POSITIONS])), 2)}
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


def tap_area():
    """Taps on the time and on the heart rate open the big live pulse."""
    def at(pid, layout, x, y):
        if layout == "mid":
            return tap_box("TimeTap", 225, TIME_CY, 2 * DIGITS_W + MID_W, TIME_SIZE)
        return "\n".join([tap_box("TimeTap", 225, TIME_CY, 2 * DIGITS_W + text_width(":", "jost_time", TIME_SIZE), TIME_SIZE),
                          tap_box("HeartTap", hr_x(x), y if layout == "h" else y - 8, 90, 60)])
    return f"""<!-- Tap on the time / heart rate: big live pulse -->
{choice("hrPos", [(pid, at(pid, lay, x, y)) for pid, _, lay, x, y in HR_POSITIONS])}"""


def temperature():
    """Orange dot, then the temperature, centered as one group."""
    return f"""<!-- Temperature (while the watch has weather) -->
<Condition>
  <Expressions>
    <Expression name="hasWeather">[WEATHER.IS_AVAILABLE]</Expression>
  </Expressions>
  <Compare expression="hasWeather">
    <Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="Weather">
{indent(choice("hrPos", [(pid, choice("textSize", [(oid, temperature_at(TEMP_SIZE * k, TEMP_SHIFT.get(pid, 0)))
                                                  for oid, _, k in TEXT_SIZES]))
                         for pid, *_ in HR_POSITIONS]), 6)}
    </Group>
  </Compare>
</Condition>"""


def temperature_at(size, shift=0):
    dot = size * 0.32
    cy = p(450 - 44 - size * LINE / 2 + shift)
    tw = text_width("25°", "jost_regular", size, 0.08)
    gw = dot + 6 + tw
    temp = text(template("[WEATHER.TEMPERATURE]", "%s°"), p(225 - gw / 2 + dot + 6), cy, s(size),
                font="jost_regular", color=ORANGE, align="START", width=s(size * 4), spacing=0.08)
    return f"""{disc(p(225 - gw / 2 + dot / 2), cy, s(dot), ORANGE)}
{temp}"""


def background():
    return f"""<!-- Dial: soft radial gradient (black in always-on) -->
<PartDraw x="0" y="0" width="{SIZE}" height="{SIZE}">
  {AMBIENT_HIDE}
  <Rectangle x="0" y="0" width="{SIZE}" height="{SIZE}">
    <Fill color="#ff0f1014">
      <RadialGradient centerX="{C:g}" centerY="{round(SIZE * 0.45)}" radius="{round(SIZE * 0.56)}" colors="#ff0f1014 #ff050506" positions="0 1" />
    </Fill>
  </Rectangle>
</PartDraw>"""


def strings():
    colors = "\n".join(f'    <string name="colors_{oid}">{label.replace("&", "&amp;")}</string>'
                       for oid, label, _, _ in COLOR_OPTIONS)
    toggles = "\n".join(f'    <string name="{tid}_label">{label}</string>' for tid, label in TOGGLES)
    toggles += "\n" + "\n".join(
        f'    <string name="{lid}_label">{label}</string>\n' + "\n".join(
            f'    <string name="{lid}_{o[0]}">{o[1]}</string>' for o in opts)
        for lid, label, _, opts in LISTS)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!-- GENERATED by fluid3face/generate_watchface.py -->
<resources>
    <string name="watch_face_name">MySteps Fluid v3</string>
    <string name="mysteps_slot_label">Inner ring (MySteps)</string>
    <string name="azm_slot_label">Outer ring (Zone Minutes)</string>
    <string name="colors_label">Colors</string>
{toggles}
{colors}
</resources>
"""


def watchface():
    zone_x, steps_x = value_cols()
    scene = "\n\n".join([
        background(),
        ring_slot(1, "azm_slot_label",
                  "com.fitbit.FitbitMobile/com.google.android.wearable.fitbit.mainapp.complications.offloadable.azm.OffloadableAZMComplicationDataSourceService",
                  RING_AZM_R, ACCENT, 36, zone_x, "showAzm", 1, 45,
                  "Outer ring + left number: Active Zone Minutes (Fitbit) by default", C),
        ring_slot(0, "mysteps_slot_label",
                  "com.adrianp.mysteps/com.adrianp.mysteps.complication.HourlyStepsComplicationService",
                  RING_STEPS_R, MAIN, 26, steps_x, "showSteps", 50, 30,
                  "Inner ring + right number: MySteps, steps this hour",
                  s(RING_STEPS_R + BAND / 2 + 1) + 1, full_at_max_one=True),
        seconds_ring(),
        date(),
        time(),
        heart_rate(),
        temperature(),
        hands(),
        tap_area(),
    ])
    color_opts = "\n".join(
        f'<ColorOption id="{oid}" displayName="colors_{oid}" screenReaderText="colors_{oid}" colors="{main} {acc}" />'
        for oid, _, main, acc in COLOR_OPTIONS)
    toggles = "\n".join(
        f'<BooleanConfiguration id="{tid}" displayName="{tid}_label" screenReaderText="{tid}_label" defaultValue="TRUE" />'
        for tid, _ in TOGGLES)
    lists = "\n".join(
        f'<ListConfiguration id="{lid}" displayName="{lid}_label" screenReaderText="{lid}_label" defaultValue="{default}">\n'
        + "\n".join(f'  <ListOption id="{o[0]}" displayName="{lid}_{o[0]}" screenReaderText="{lid}_{o[0]}" />' for o in opts)
        + "\n</ListConfiguration>"
        for lid, _, default, opts in LISTS)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!-- GENERATED by fluid3face/generate_watchface.py — edit that file, not this one. -->
<WatchFace width="{SIZE}" height="{SIZE}" clipShape="CIRCLE">
  <Metadata key="CLOCK_TYPE" value="DIGITAL" />
  <Metadata key="PREVIEW_TIME" value="10:08:32" />

  <UserConfigurations>
    <ColorConfiguration id="themeColor" displayName="colors_label" defaultValue="{COLOR_OPTIONS[0][0]}">
{indent(color_opts, 6)}
    </ColorConfiguration>
{indent(lists, 4)}
{indent(toggles, 4)}
  </UserConfigurations>

  <Scene backgroundColor="#ff000000">
{indent(scene, 4)}
  </Scene>
</WatchFace>
"""


if __name__ == "__main__":
    OUT.write_text(watchface())
    (RES / "values/strings.xml").write_text(strings())
    print(f"wrote {OUT}")
