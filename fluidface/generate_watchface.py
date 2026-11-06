#!/usr/bin/env python3
"""Generates src/main/res/raw/watchface.xml for the Fluid watch face.

Edit this file, not the XML:

    python3 fluidface/generate_watchface.py

The layout follows the "Cadran Fluid v2" design (450 px HTML mock-up), scaled to the
Pixel Watch 3's 456 px: concentric rings for Active Zone Minutes (outer), MySteps steps
this hour (middle) and heart rate (inner), the date on top, a big light time with an
accent colon, a row of numbers below and the temperature at the bottom. The rings touch
(no gaps) so the text can be ~20 % bigger than in the mock-up. Like activeface,
it is not offloadable, so raising the wrist wakes Android and MySteps refreshes.
"""
from pathlib import Path
from fontTools.ttLib import TTFont

HERE = Path(__file__).parent
RES = HERE / "src/main/res"
OUT = RES / "raw/watchface.xml"

SIZE = 456
K = SIZE / 450                   # design px -> watch px
C = SIZE / 2


# The rings sit edge to edge at the rim (watch px), so the content gets the room the
# design spent on gaps: everything inside is scaled up by CONTENT about the center
CONTENT = 1.22
KC = K * CONTENT
RING_AZM = (220, 14)        # (mid radius, stroke): 213..227
RING_STEPS = (209, 8)       # 205..213
RING_HR = (202.5, 5)        # 200..205


def s(v):
    """Design size to watch size (rounded to 0.1 px)."""
    return round(v * KC, 1)


def p(v):
    """Design coordinate (x or y) to watch coordinate, scaled about the center."""
    return round(C + (v - 225) * KC, 1)


# Customize → Colors: (id, label, main, accent); the first is the default (the design)
COLOR_OPTIONS = [
    ("sand", "Sand & blue", "#ffe9c98c", "#ff7d96ea"),
    ("mint", "Mint & pink", "#ff6de18b", "#ffe3a6dd"),
    ("lilac", "Lilac Bliss", "#ffc9b6ec", "#ff9b84d6"),
    ("teal", "Fitbit Teal", "#ff39cccc", "#ffe2e2e2"),
    ("azm", "Zone Minutes", "#fff8c33c", "#fff57c3a"),
    ("mono", "Silver", "#ffe2e2e2", "#ff8f9bb3"),
]
MAIN = "[CONFIGURATION.themeColor.0]"    # time, date, bpm, steps ring
ACCENT = "[CONFIGURATION.themeColor.1]"  # colon, zone minutes ring and numbers
RED = "#ffe5493f"                        # heart-rate ring and heart
ORANGE = "#ffe39a5a"                     # temperature
HR_MAX = 145                             # the inner ring spans 0..145 bpm (89 bpm ≈ 62 %)

# Date and temperature, bigger than the mock-up (12-14 px read badly on the wrist)
DAY_SIZE, MONTH_SIZE, TEMP_SIZE = 34, 17, 24

MONTHS = ["IAN", "FEB", "MAR", "APR", "MAI", "IUN", "IUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

AMBIENT_HIDE = '<Variant mode="AMBIENT" target="alpha" value="0" />'

FONT_FILES = {name: TTFont(RES / "font" / f"{name}.ttf") for name in ("sg_light", "sg_regular", "sg_medium", "sg_time")}


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


def text(content, cx, cy, size, font="sg_medium", color=MAIN, width=None, extra="",
         spacing=0.0, align="CENTER", inner=""):
    """Single-line text whose cap middle sits on (cx, cy) (Space Grotesk's line box is
    centered on its caps, within 0.5 % of the size). align=START puts the left edge at cx,
    END the right edge."""
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


def image(resource, x, y, w, h, extra="", tint=None):
    t = f' tintColor="{tint}"' if tint else ""
    return f"""<PartImage x="{round(x)}" y="{round(y)}" width="{round(w)}" height="{round(h)}"{t}{extra}>
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
    """Progress arc with a soft halo (two wider, faint strokes behind; the design's
    CSS drop-shadow). The halo is dropped in always-on."""
    halo = [arc(r, stroke + glow * k, color, fraction, alpha=a, extra=f"\n  {AMBIENT_HIDE}")
            for k, a in ((1.6, 22), (0.8, 45))]
    return "\n".join(halo + [arc(r, stroke, color, fraction)])


def disc(cx, cy, d, color, extra=""):
    import math
    x, y = math.floor(cx - d / 2), math.floor(cy - d / 2)
    box = math.ceil(max(cx + d / 2 - x, cy + d / 2 - y))
    return f"""<PartDraw x="{x}" y="{y}" width="{box}" height="{box}"{extra}>
  <Ellipse x="{cx - d / 2 - x:g}" y="{cy - d / 2 - y:g}" width="{d:g}" height="{d:g}">
    <Fill color="{color}" />
  </Ellipse>
</PartDraw>"""


RANGED = ("(clamp([COMPLICATION.RANGED_VALUE_VALUE], [COMPLICATION.RANGED_VALUE_MIN], "
          "[COMPLICATION.RANGED_VALUE_MAX]) - [COMPLICATION.RANGED_VALUE_MIN]) / "
          "([COMPLICATION.RANGED_VALUE_MAX] - [COMPLICATION.RANGED_VALUE_MIN])")
GOAL = "[COMPLICATION.GOAL_PROGRESS_VALUE] / [COMPLICATION.GOAL_PROGRESS_TARGET_VALUE]"

# ---- Bottom row: three columns, flex-centered with a 22 px gap (design px) ----------
LABEL_SIZE, LABEL_LS = 13, 0.12
ROW_BOTTOM = 450 - 118
LABEL_CY = ROW_BOTTOM - LABEL_SIZE * 1.276 / 2          # line-height: normal (1.276 em)
# Numbers are bigger than the mock-up's 22 / 26 px (asked for on the watch)
VALUE_SIZE = 36                                   # zone minutes and steps this hour
BPM_SIZE = 40                                     # heart-rate number
VALUE_CY = ROW_BOTTOM - LABEL_SIZE * 1.276 - 3 - VALUE_SIZE / 2  # gap 3 above the label line
BPM_CY = ROW_BOTTOM - LABEL_SIZE * 1.276 - 3 - BPM_SIZE / 2
HEART_SIZE = 28                                   # ♥ glyph box; drawn as an icon


def columns():
    """Column centers (design px) for typical values, like the design's flexbox."""
    # Only the steps number has a label (zone minutes and bpm read on their own)
    labels = ["", "", "PAȘI / H"]
    values = [text_width("77", "sg_medium", VALUE_SIZE),
              HEART_SIZE + 6 + text_width("89", "sg_medium", BPM_SIZE),
              text_width("180", "sg_medium", VALUE_SIZE)]
    widths = [max(v, text_width(l, "sg_regular", LABEL_SIZE, LABEL_LS) if l else 0) for l, v in zip(labels, values)]
    x = 225 - (sum(widths) + 2 * 22) / 2
    centers = []
    for w in widths:
        centers.append(x + w / 2)
        x += w + 22
    return labels, centers


LABELS, COLS = columns()


def label(i):
    return text(LABELS[i], p(COLS[i]) + s(LABEL_SIZE * LABEL_LS) / 2, p(LABEL_CY), s(LABEL_SIZE),
                font="sg_regular", width=s(80), spacing=LABEL_LS, extra=' alpha="140"')


def ring_slot(slot_id, name, provider, r, stroke, glow, color, track_alpha, col, value_color,
              comment, area, full_at_max_one=False):
    """Complication slot drawing its ring plus its number (and label) in the bottom row.
    The watch clips a complication to its bounding shape (one per slot), so area is a
    centered oval of that radius: the outer slot covers the screen, the inner one the
    disc inside, so taps on the outer band go to the outer ring's provider."""
    def body(kind, fraction):
        parts = [arc(r, stroke, color, alpha=track_alpha, extra=f"\n  {AMBIENT_HIDE}")]
        if fraction:
            if full_at_max_one:
                # MySteps sends value 0 of max 1 once the hour's goal is met: full ring then
                fraction = f"([COMPLICATION.RANGED_VALUE_MAX] == 1 ? 1 : {fraction})"
            parts.append(glowing_arc(r, stroke, color, fraction, glow) if glow
                         else arc(r, stroke, color, fraction))
        if kind != "EMPTY":
            parts.append(text(template("[COMPLICATION.TEXT]"), p(COLS[col]), p(VALUE_CY), s(VALUE_SIZE),
                              color=value_color, width=s(VALUE_SIZE * 3.2)))
        else:
            parts.append(text("--", p(COLS[col]), p(VALUE_CY), s(VALUE_SIZE), color=value_color,
                              width=s(VALUE_SIZE * 3.2)))
        if LABELS[col]:
            parts.append(label(col))
        return f"""<Complication type="{kind}">
{indent(chr(10).join(parts), 2)}
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


def heart_rate():
    """Inner red ring (bpm / HR_MAX), heart and number in the middle column."""
    r, w = RING_HR
    frac = f"[HEART_RATE] / {HR_MAX}"
    num_w = text_width("89", "sg_medium", BPM_SIZE)
    group_w = HEART_SIZE + 6 + num_w
    hx = p(COLS[1] - group_w / 2)                     # heart box left
    nx = p(COLS[1] - group_w / 2 + HEART_SIZE + 6)    # number left
    hs = s(HEART_SIZE * 0.83)                         # visible heart in the glyph box
    number = text(template("round([HEART_RATE])"), nx, p(BPM_CY), s(BPM_SIZE), align="START",
                  width=s(BPM_SIZE * 2.6))
    dashes = text("--", nx, p(BPM_CY), s(BPM_SIZE), align="START", width=s(BPM_SIZE * 2.6))
    return f"""<!-- Heart rate: inner ring, ♥ and bpm -->
{arc(r, w, RED, alpha=20, extra=f"{chr(10)}  {AMBIENT_HIDE}")}
<Condition>
  <Expressions>
    <Expression name="hasHr">[HEART_RATE] &gt; 0</Expression>
  </Expressions>
  <Compare expression="hasHr">
{indent(arc(r, w, RED, frac), 4)}
{indent(number, 4)}
  </Compare>
  <Default>
{indent(dashes, 4)}
  </Default>
</Condition>
{image("ic_heart", hx + (s(HEART_SIZE) - hs) / 2, p(BPM_CY) - hs * 0.89 / 2, hs, hs * 0.89, tint=RED)}"""


def seconds_dot():
    """The design's drifting dot on the outer ring, here moving with the seconds."""
    r = RING_AZM[0]
    theta = "rad([SECOND] * 6)"
    d = 10
    return f"""<!-- Seconds dot on the outer ring (hidden in always-on) -->
<Group x="0" y="0" width="{round(d + 4)}" height="{round(d + 4)}" name="SecondsDot">
  <Transform target="x" value="{C:g} + {r} * sin({theta}) - {(d + 4) / 2:g}" />
  <Transform target="y" value="{C:g} - {r} * cos({theta}) - {(d + 4) / 2:g}" />
  {AMBIENT_HIDE}
{indent(disc((d + 4) / 2, (d + 4) / 2, d + 4, MAIN, extra=' alpha="60"'), 2)}
{indent(disc((d + 4) / 2, (d + 4) / 2, d, MAIN), 2)}
</Group>"""


def date():
    month = template(chain("[MONTH]", [m + "." for m in MONTHS]))
    return f"""<!-- Date: day of the month, month below -->
{text(template("[DAY]"), C, p(84 + DAY_SIZE / 2), s(DAY_SIZE), width=s(DAY_SIZE * 3))}
{text(month, C + s(MONTH_SIZE * 0.14) / 2, p(84 + DAY_SIZE + 2 + MONTH_SIZE * 1.276 / 2), s(MONTH_SIZE),
      font="sg_medium", width=s(MONTH_SIZE * 7), spacing=0.14, extra=' alpha="170"')}"""


def time():
    """hh : mm, light 100 px digits (tabular, -0.05 em), accent colon pulsing each second."""
    size = 100
    ls = -0.05
    cy = p((450 - 24) / 2)
    colon_w = text_width(":", "sg_light", size, ls) + 4        # margin 0 2px
    digits_w = text_width("00", "sg_light", size, ls)
    left = 225 - (2 * digits_w + colon_w) / 2
    hh_right, mm_left = left + digits_w, left + digits_w + colon_w
    colon_cx = hh_right + colon_w / 2
    h = round(s(size) * 1.6)
    w = round(s(digits_w + 20))

    def clock(fmt, x_edge, align):
        x = x_edge if align == "START" else x_edge - w
        return f"""<DigitalClock x="{round(x)}" y="{round(cy - h / 2)}" width="{w}" height="{h}">
  <TimeText format="{fmt}" hourFormat="SYNC_TO_DEVICE" align="{align}" x="0" y="0" width="{w}" height="{h}">
    <Font family="sg_time" size="{s(size):g}" color="{MAIN}" />
  </TimeText>
</DigitalClock>"""
    pulse = ('\n  <Transform target="alpha" value="[SECOND] % 2 == 0 ? 255 : 140" />'
             '\n  <Variant mode="AMBIENT" target="alpha" value="255" />')
    # sg_time has the tracking in its advances, like the browser (after every glyph)
    return f"""<!-- Time -->
{clock("hh", p(hh_right), "END")}
{text(":", p(colon_cx) - s(size * ls) / 2, cy, s(size), font="sg_light", color=ACCENT, width=s(40), inner=pulse)}
{clock("mm", p(mm_left), "START")}"""


def temperature():
    """Orange dot with a halo, then the temperature, centered as one group."""
    size, dot = TEMP_SIZE, TEMP_SIZE * 0.45
    cy = p(450 - 76 - size * 1.276 / 2)
    tw = text_width("25°", "sg_medium", size, 0.02)
    gw = dot + 6 + tw
    dot_cx = p(225 - gw / 2 + dot / 2)
    tx = p(225 - gw / 2 + dot + 6)
    temp = text(template("[WEATHER.TEMPERATURE]", "%s°"), tx, cy, s(size), color=ORANGE,
                align="START", width=s(size * 3.5), spacing=0.02)
    return f"""<!-- Temperature -->
<Condition>
  <Expressions>
    <Expression name="hasWeather">[WEATHER.IS_AVAILABLE]</Expression>
  </Expressions>
  <Compare expression="hasWeather">
{indent(disc(dot_cx, cy, s(dot * 1.75), ORANGE, extra=' alpha="64"'), 4)}
{indent(disc(dot_cx, cy, s(dot), ORANGE), 4)}
{indent(temp, 4)}
  </Compare>
</Condition>"""


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


def color_option(option):
    oid, _, main, accent = option
    return (f'<ColorOption id="{oid}" displayName="colors_{oid}" screenReaderText="colors_{oid}"\n'
            f'    colors="{main} {accent}" />')


def strings():
    lines = "\n".join(f'    <string name="colors_{oid}">{label.replace("&", "&amp;")}</string>'
                      for oid, label, _, _ in COLOR_OPTIONS)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!-- GENERATED by fluidface/generate_watchface.py -->
<resources>
    <string name="watch_face_name">MySteps Fluid</string>
    <string name="mysteps_slot_label">Middle ring (MySteps)</string>
    <string name="azm_slot_label">Outer ring (Zone Minutes)</string>
    <string name="colors_label">Colors</string>
{lines}
</resources>
"""


def watchface():
    scene = "\n\n".join([
        background(),
        ring_slot(1, "azm_slot_label",
                  "com.fitbit.FitbitMobile/com.google.android.wearable.fitbit.mainapp.complications.offloadable.azm.OffloadableAZMComplicationDataSourceService",
                  *RING_AZM, 8, ACCENT, 31, 0, ACCENT,
                  "Outer ring + left number: Active Zone Minutes (Fitbit) by default", C),
        ring_slot(0, "mysteps_slot_label",
                  "com.adrianp.mysteps/com.adrianp.mysteps.complication.HourlyStepsComplicationService",
                  *RING_STEPS, 0, MAIN, 20, 2, ACCENT,
                  "Middle ring + right number: MySteps, steps this hour", RING_STEPS[0] + RING_STEPS[1] / 2 + 1, full_at_max_one=True),
        heart_rate(),
        seconds_dot(),
        date(),
        time(),
        temperature(),
    ])
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!-- GENERATED by fluidface/generate_watchface.py — edit that file, not this one. -->
<WatchFace width="{SIZE}" height="{SIZE}" clipShape="CIRCLE">
  <Metadata key="CLOCK_TYPE" value="DIGITAL" />
  <Metadata key="PREVIEW_TIME" value="10:08:32" />

  <UserConfigurations>
    <ColorConfiguration id="themeColor" displayName="colors_label" defaultValue="{COLOR_OPTIONS[0][0]}">
{indent(chr(10).join(color_option(o) for o in COLOR_OPTIONS), 6)}
    </ColorConfiguration>
  </UserConfigurations>

  <Scene backgroundColor="#ff000000">
{indent(scene, 4)}
  </Scene>
</WatchFace>
"""


if __name__ == "__main__":
    OUT.write_text(watchface())
    (RES / "values/strings.xml").write_text(strings())
    print(f"wrote {OUT}", "columns:", [round(c, 1) for c in COLS])
