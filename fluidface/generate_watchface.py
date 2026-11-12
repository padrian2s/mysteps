#!/usr/bin/env python3
"""Generates src/main/res/raw/watchface.xml for the Fluid watch face.

Fonts: Space Grotesk (the design's) or JetBrains Mono, picked in Customize → Font.

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
    # Early Ubuntu themes (approximations of their GTK palettes, brightened for a black dial)
    ("warty", "Warty Brown", "#ffe8c9a1", "#ffc08850"),      # 4.10: brown everything
    ("human", "Human", "#fff2d2a9", "#fff57900"),            # 5.04-9.04: tan + Human orange
    ("earth", "Human Earth", "#ffd8c3a5", "#ff9aae62"),      # earthy tan + olive green
    ("spirit", "Human Spirit", "#ffffd9a0", "#ffe95420"),    # warm cream + Ubuntu orange
    ("gaia", "Gaia", "#ffc9dca0", "#ff73a24a"),              # leafy greens
    ("ambiance", "Ambiance", "#ffdfdbd2", "#fff07746"),      # 10.04: warm grey + orange
    ("aubergine", "Aubergine", "#fff6a37a", "#ffb37aa8"),    # orange on light aubergine
]
MAIN = "[CONFIGURATION.themeColor.0]"    # time, date, bpm, steps ring
ACCENT = "[CONFIGURATION.themeColor.1]"  # colon, zone minutes ring and numbers
RED = "#ffe5493f"                        # heart-rate ring and heart
ORANGE = "#ffe39a5a"                     # temperature
# Black dots on the filled rings: steps one per 50 (max 30), Zone Minutes one per minute (max 45).
# A met MySteps hour carries no goal (max 1): dots for the 300-step goal (6)
STEP_GOAL_DOTS = 6
HR_ACTIVE, HR_CARDIO = 100, 130          # inner ring zones: rest dim red, active orange, cardio bright red

# Date and temperature, bigger than the mock-up (12-14 px read badly on the wrist)
DAY_SIZE, MONTH_SIZE, TEMP_SIZE = 34, 17, 24

MONTHS = ["IAN", "FEB", "MAR", "APR", "MAI", "IUN", "IUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

AMBIENT_HIDE = '<Variant mode="AMBIENT" target="alpha" value="0" />'

# Customize → Font: (id = font file prefix, label); the first is the default (the design's)
FAMILIES = [("sg", "Space Grotesk"), ("jb", "JetBrains Mono")]
FAMILY = "sg"   # family being generated; code names fonts as "sg_<role>" and this swaps it

FONT_FILES = {f"{fid}_{role}": TTFont(RES / "font" / f"{fid}_{role}.ttf")
              for fid, _ in FAMILIES for role in ("light", "medium", "time")}


def font(name):
    """sg_<role> -> <current family>_<role>."""
    return FAMILY + name[2:] if name.startswith("sg_") else name


# Customize → Layout: (id, label). "heart" is the second mock-up: ♥ and bpm between the
# hours and minutes instead of the colon, zone minutes and steps alone on the row below
LAYOUTS = [("classic", "Classic"), ("heart", "Heart in the time")]
LAYOUT = "classic"


def per_option(config_id, items, var, make):
    """ListConfiguration with one Group per option, each holding make() built while the
    module global var is set to that option."""
    variants = {}
    for oid, _ in items:
        globals()[var] = oid
        variants[oid] = make()
    globals()[var] = items[0][0]
    opts = "\n".join(f"""<ListOption id="{oid}">
  <Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="{config_id}_{oid}">
{indent(xml, 4)}
  </Group>
</ListOption>""" for oid, xml in variants.items())
    return f"""<ListConfiguration id="{config_id}">
{indent(opts, 2)}
</ListConfiguration>"""


TOGGLES = [("showSteps", "Steps number"), ("showAzm", "Zone Minutes number"),
           ("showHr", "Heart rate number")]


def toggle(config_id, xml):
    """Customize on/off switch (default on): xml drawn only when the switch is on."""
    return f"""<BooleanConfiguration id="{config_id}">
  <BooleanOption id="TRUE">
    <Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="{config_id}">
{indent(xml, 6)}
    </Group>
  </BooleanOption>
</BooleanConfiguration>"""


def per_font(make):
    """Customize → Font: make() once per family."""
    return per_option("font", FAMILIES, "FAMILY", make)


def per_layout(make):
    """Customize → Layout: make() once per layout."""
    return per_option("layout", LAYOUTS, "LAYOUT", make)


def per_style(make):
    """Every layout x font combination."""
    return per_layout(lambda: per_font(make))


def text_width(content, font, size, spacing=0.0):
    """Advance width in px, as the browser lays it out (letter-spacing after every glyph)."""
    f = FONT_FILES[globals()["font"](font)]
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
    """Single-line text whose cap middle sits on (cx, cy) (Space Grotesk's and JetBrains
    Mono's line boxes are centered on their caps, within 0.5 % of the size). align=START puts the left edge at cx,
    END the right edge."""
    w = round(width or SIZE)
    h = round(size * 1.6)
    x = {"CENTER": cx - w / 2, "START": cx, "END": cx - w}[align]
    ls = f' letterSpacing="{spacing:g}"' if spacing else ""
    return f"""<PartText x="{round(x)}" y="{round(cy - h / 2)}" width="{w}" height="{h}"{extra}>{inner}
  <Text align="{align}">
    <Font family="{globals()["font"](font)}" size="{size:g}" color="{color}"{ls}>{content}</Font>
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
    """Progress arc with a soft halo (two wider, faint strokes behind; the design's
    CSS drop-shadow). The halo is dropped in always-on."""
    halo = [arc(r, stroke + glow * k, color, fraction, alpha=a, extra=f"\n  {AMBIENT_HIDE}")
            for k, a in ((1.6, 22), (0.8, 45))]
    return "\n".join(halo + [arc(r, stroke, color, fraction)])


def disc(cx, cy, d, color, extra="", inner=""):
    import math
    x, y = math.floor(cx - d / 2), math.floor(cy - d / 2)
    box = math.ceil(max(cx + d / 2 - x, cy + d / 2 - y))
    return f"""<PartDraw x="{x}" y="{y}" width="{box}" height="{box}"{extra}>{inner}
  <Ellipse x="{cx - d / 2 - x:g}" y="{cy - d / 2 - y:g}" width="{d:g}" height="{d:g}">
    <Fill color="{color}" />
  </Ellipse>
</PartDraw>"""


RANGED = ("(clamp([COMPLICATION.RANGED_VALUE_VALUE], [COMPLICATION.RANGED_VALUE_MIN], "
          "[COMPLICATION.RANGED_VALUE_MAX]) - [COMPLICATION.RANGED_VALUE_MIN]) / "
          "([COMPLICATION.RANGED_VALUE_MAX] - [COMPLICATION.RANGED_VALUE_MIN])")
GOAL = "[COMPLICATION.GOAL_PROGRESS_VALUE] / [COMPLICATION.GOAL_PROGRESS_TARGET_VALUE]"

# ---- Bottom row: three columns, flex-centered with a 22 px gap (design px) ----------
LABEL_SIZE = 13      # the labels are gone; the row keeps the room their line took
ROW_BOTTOM = 450 - 111
# Numbers are bigger than the mock-up's 22 / 26 px (asked for on the watch)
VALUE_SIZE = 36                                   # zone minutes and steps this hour
BPM_SIZE = 40                                     # heart-rate number
VALUE_CY = ROW_BOTTOM - LABEL_SIZE * 1.276 - 3 - VALUE_SIZE / 2  # gap 3 above the label line
BPM_CY = ROW_BOTTOM - LABEL_SIZE * 1.276 - 3 - BPM_SIZE / 2
HEART_SIZE = 28                                   # ♥ glyph box; drawn as an icon
# Heart layout (design px): middle gap of the number row, time size and gap, ♥ and bpm
HEART_GAP = 62
HEART_ROW_CY = 316
HEART_TIME_SIZE, HEART_TIME_GAP, HEART_TIME_CY = 88, 60, 219
HEART_ICON, HEART_ICON_CY = 20, 203
HEART_BPM_SIZE, HEART_BPM_CY = 30, 244     # bigger than the mock-up's, asked for on the watch


def value_cy():
    return HEART_ROW_CY if LAYOUT == "heart" else VALUE_CY


def cols():
    """Column centers (design px) for typical values, like the design's flexbox. No labels:
    the numbers read on their own (colors tell them apart)."""
    if LAYOUT == "heart":
        # Two numbers far apart; the middle one is empty (the bpm is in the time)
        widths = [text_width("77", "sg_medium", VALUE_SIZE), HEART_GAP,
                  text_width("180", "sg_medium", VALUE_SIZE)]
    else:
        widths = [text_width("77", "sg_medium", VALUE_SIZE),
                  HEART_SIZE + 6 + text_width("188", "sg_medium", BPM_SIZE),   # room for 100 and up
                  text_width("180", "sg_medium", VALUE_SIZE)]
    x = 225 - (sum(widths) + 2 * 22) / 2
    centers = []
    for w in widths:
        centers.append(x + w / 2)
        x += w + 22
    return centers


def ring_ticks(r, d, value, maxv, unit, cap, goal_met=None, fallback=None):
    """Black dots on the filled part of a progress ring, one per unit (e.g. 50 steps,
    1 minute) of the goal maxv, at most cap (beyond that a dot is worth maxv / cap).
    goal_met / fallback: when goal_met is true the data has no goal: fallback dots, ring full."""
    n = f"clamp(round({maxv} / {unit}), 1, {cap})"
    done = f"({value} * {n} / {maxv})"      # filled length in dots
    if goal_met:
        n = f"({goal_met} ? {fallback} : {n})"
        done = f"({goal_met} ? {fallback} : {done})"
    box = d + 2
    dots = []
    for i in range(1, cap):                 # none at 12 o'clock, where the ring starts
        theta = f"rad({i} * 360 / {n})"
        dots.append(f"""<Group x="0" y="0" width="{box}" height="{box}" name="Tick{i}">
  <Transform target="x" value="{C:g} + {r} * sin({theta}) - {box / 2:g}" />
  <Transform target="y" value="{C:g} - {r} * cos({theta}) - {box / 2:g}" />
  <Transform target="alpha" value="{i} &lt; {n} &amp;&amp; {i} &lt; {done} ? 255 : 0" />
{indent(disc(box / 2, box / 2, d, "#ff000000"), 2)}
</Group>""")
    return "\n".join(dots)


def ring_slot(slot_id, name, provider, r, stroke, glow, color, track_alpha, col, value_color,
              comment, area, toggle_id, dot, unit, cap, full_at_max_one=False):
    """Complication slot drawing its ring plus its number (and label) in the bottom row.
    The watch clips a complication to its bounding shape (one per slot), so area is a
    centered oval of that radius: the outer slot covers the screen, the inner one the
    disc inside, so taps on the outer band go to the outer ring's provider."""
    def body(kind, fraction):
        parts = [arc(r, stroke, color, alpha=track_alpha, extra=f"\n  {AMBIENT_HIDE}")]
        if fraction:
            met = None
            if full_at_max_one:
                # MySteps sends value 0 of max 1 once the hour's goal is met: full ring then
                met = "[COMPLICATION.RANGED_VALUE_MAX] == 1"
                if kind == "RANGED_VALUE":
                    fraction = f"({met} ? 1 : {fraction})"
            parts.append(glowing_arc(r, stroke, color, fraction, glow) if glow
                         else arc(r, stroke, color, fraction))
            value, maxv = (("[COMPLICATION.RANGED_VALUE_VALUE]", "[COMPLICATION.RANGED_VALUE_MAX]")
                           if kind == "RANGED_VALUE" else
                           ("[COMPLICATION.GOAL_PROGRESS_VALUE]", "[COMPLICATION.GOAL_PROGRESS_TARGET_VALUE]"))
            parts.append(ring_ticks(r, dot, value, maxv, unit, cap,
                                    met if kind == "RANGED_VALUE" else None, STEP_GOAL_DOTS))
        def number():
            if kind == "EMPTY":
                return text("--", p(cols()[col]), p(value_cy()), s(VALUE_SIZE), color=value_color,
                            width=s(VALUE_SIZE * 3.2))
            def at(expr, size, inner=""):
                return text(template(expr), p(cols()[col]), p(value_cy()), s(size),
                            color=value_color, width=s(VALUE_SIZE * 3.2), inner=inner)
            if not (full_at_max_one and kind == "RANGED_VALUE"):
                return at("[COMPLICATION.TEXT]", VALUE_SIZE)
            # Goal met: MySteps sends "❤N/M" (just "❤" in the day's first hour). The full
            # ring already says it: drop the ❤ and draw the longer "N/M" smaller
            is_met = "[COMPLICATION.RANGED_VALUE_MAX] == 1"
            hours = ("textLength([COMPLICATION.TEXT]) &gt; 1 ? subText([COMPLICATION.TEXT], 1, "
                     "textLength([COMPLICATION.TEXT])) : [COMPLICATION.TEXT]")
            return "\n".join([
                at("[COMPLICATION.TEXT]", VALUE_SIZE, f'\n  <Transform target="alpha" value="{is_met} ? 0 : 255" />'),
                at(hours, VALUE_SIZE * 0.7, f'\n  <Transform target="alpha" value="{is_met} ? 255 : 0" />')])
        # Complications only take parts, groups and conditions: wrap the font options
        # The number can be switched off in Customize; the ring stays
        parts.append(f"""<Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="Number">
{indent(toggle(toggle_id, per_style(number)), 2)}
</Group>""")
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
    """Inner ring, always a full circle colored by heart rate zone (not a progress bar:
    a resting 65 bpm used to read as a half-done ring), then ♥ and bpm placed by the layout."""
    r, w = RING_HR
    zones = "".join(f"""
    <Compare expression="{name}">
{indent(ring, 6)}
    </Compare>""" for name, ring in (
        ("hrCardio", glowing_arc(r, w, RED, None, 6)),
        ("hrActive", arc(r, w, ORANGE, alpha=210)),
        ("hrRest", arc(r, w, RED, alpha=95)),
    ))
    # Hidden in always-on: the bpm only updates while the screen is on
    return f"""<!-- Heart rate: inner zone ring, ♥ and bpm (screen on only) -->
<Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="HeartRate">
  {AMBIENT_HIDE}
  <Condition>
    <Expressions>
      <Expression name="hrCardio">[HEART_RATE] &gt;= {HR_CARDIO}</Expression>
      <Expression name="hrActive">[HEART_RATE] &gt;= {HR_ACTIVE}</Expression>
      <Expression name="hrRest">[HEART_RATE] &gt; 0</Expression>
    </Expressions>{zones}
    <Default>
{indent(arc(r, w, RED, alpha=20), 6)}
    </Default>
  </Condition>
{indent(per_style(heart_rate_variant), 2)}
</Group>"""


def heart_rate_variant():
    if LAYOUT == "heart":
        return heart_in_time()
    num_w = text_width("89", "sg_medium", BPM_SIZE)
    group_w = HEART_SIZE + 6 + num_w
    hx = p(cols()[1] - group_w / 2)                   # heart box left
    nx = p(cols()[1] - group_w / 2 + HEART_SIZE + 6)  # number left
    hs = s(HEART_SIZE * 0.83)                         # visible heart in the glyph box
    number = text(template("round([HEART_RATE])"), nx, p(BPM_CY), s(BPM_SIZE), align="START",
                  width=s(BPM_SIZE * 2.6))
    dashes = text("--", nx, p(BPM_CY), s(BPM_SIZE), align="START", width=s(BPM_SIZE * 2.6))
    return toggle("showHr", f"""<!-- Heart rate: ♥ and bpm in the middle of the row -->
<Condition>
  <Expressions>
    <Expression name="hasHr">[HEART_RATE] &gt; 0</Expression>
  </Expressions>
  <Compare expression="hasHr">
{indent(number, 4)}
  </Compare>
  <Default>
{indent(dashes, 4)}
  </Default>
</Condition>
{image("ic_heart", hx + (s(HEART_SIZE) - hs) / 2, p(BPM_CY) - hs * 0.89 / 2, hs, hs * 0.89, tint=RED)}""")


def heart_in_time():
    """Heart layout: a glowing ♥ with the bpm under it, between hours and minutes."""
    hs = s(HEART_ICON)
    hx, hy = C - hs / 2, p(HEART_ICON_CY) - hs * 0.89 / 2
    glow = s(HEART_ICON * 1.35)
    number = text(template("round([HEART_RATE])"), C, p(HEART_BPM_CY), s(HEART_BPM_SIZE),
                  color=RED, width=s(HEART_BPM_SIZE * 3))
    dashes = text("--", C, p(HEART_BPM_CY), s(HEART_BPM_SIZE), color=RED, width=s(HEART_BPM_SIZE * 3))
    # Only the bpm can be switched off: the ♥ keeps the gap between hours and minutes
    bpm = f"""<Condition>
  <Expressions>
    <Expression name="hasHr">[HEART_RATE] &gt; 0</Expression>
  </Expressions>
  <Compare expression="hasHr">
{indent(number, 4)}
  </Compare>
  <Default>
{indent(dashes, 4)}
  </Default>
</Condition>"""
    return f"""<!-- Heart rate: ♥ and bpm in place of the colon -->
{image("ic_heart", C - glow / 2, p(HEART_ICON_CY) - glow * 0.89 / 2, glow, glow * 0.89, tint=RED,
       extra=' alpha="60"', inner=f"{chr(10)}  {AMBIENT_HIDE}")}
{image("ic_heart", hx, hy, hs, hs * 0.89, tint=RED)}
{toggle("showHr", bpm)}"""


def tap_area(name, cx, cy, w, h):
    """Invisible box (design px) that opens MySteps' full-screen live heart rate, on tap."""
    x, y, pw, ph = round(p(cx - w / 2)), round(p(cy - h / 2)), round(s(w)), round(s(h))
    return f"""<Group x="{x}" y="{y}" width="{pw}" height="{ph}" name="{name}">
  <Launch target="com.adrianp.mysteps/com.adrianp.mysteps.presentation.HeartRateActivity" />
  <PartDraw x="0" y="0" width="{pw}" height="{ph}">
    <Rectangle x="0" y="0" width="{pw}" height="{ph}">
      <Fill color="#00000000" />
    </Rectangle>
  </PartDraw>
</Group>"""


def heart_taps():
    """Tap on the time or the ♥/bpm: full-screen live pulse (MySteps HeartRateActivity)."""
    if LAYOUT == "heart":
        return tap_area("HeartTap", 225, HEART_TIME_CY, 320, HEART_TIME_SIZE * 1.1)
    group_w = HEART_SIZE + 6 + text_width("89", "sg_medium", BPM_SIZE)
    return (tap_area("TimeTap", 225, (450 - 24) / 2, 300, 100 * 0.9) + "\n"
            + tap_area("HeartTap", cols()[1], BPM_CY, group_w + 16, BPM_SIZE * 1.4))


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
    heart = LAYOUT == "heart"
    size = HEART_TIME_SIZE if heart else 100
    ls = -0.05
    cy = p(HEART_TIME_CY if heart else (450 - 24) / 2)
    # margin 0 2px; a monospace colon is as wide as a digit: keep the gap proportional.
    # The heart layout leaves room for the ♥ and bpm instead
    colon_w = HEART_TIME_GAP if heart else min(text_width(":", "sg_light", size, ls), 0.3 * size) + 4
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
    <Font family="{font('sg_time')}" size="{s(size):g}" color="{MAIN}" />
  </TimeText>
</DigitalClock>"""
    pulse = ('\n  <Transform target="alpha" value="[SECOND] % 2 == 0 ? 255 : 140" />'
             '\n  <Variant mode="AMBIENT" target="alpha" value="255" />')
    # sg_time has the tracking in its advances, like the browser (after every glyph)
    colon = "" if heart else "\n" + text(":", p(colon_cx) - s(size * ls) / 2, cy, s(size), font="sg_light",
                                          color=ACCENT, width=s(40), inner=pulse)
    return f"""<!-- Time -->
{clock("hh", p(hh_right), "END")}{colon}
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
{disc(dot_cx, cy, s(dot * 1.75), ORANGE, extra=' alpha="64"')}
{disc(dot_cx, cy, s(dot), ORANGE)}
{temp}"""


def weather():
    """Temperature only while the watch has weather; the check sits outside the font
    options (inside them it stopped showing)."""
    return f"""<Condition>
  <Expressions>
    <Expression name="hasWeather">[WEATHER.IS_AVAILABLE]</Expression>
  </Expressions>
  <Compare expression="hasWeather">
    <Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="Weather">
{indent(per_font(temperature), 6)}
    </Group>
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
    layouts = "\n".join(f'    <string name="layout_{lid}">{label}</string>' for lid, label in LAYOUTS)
    toggles = "\n".join(f'    <string name="{tid}_label">{label}</string>' for tid, label in TOGGLES)
    fonts = "\n".join(f'    <string name="font_{fid}">{label}</string>' for fid, label in FAMILIES)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!-- GENERATED by fluidface/generate_watchface.py -->
<resources>
    <string name="watch_face_name">MySteps Fluid</string>
    <string name="mysteps_slot_label">Middle ring (MySteps)</string>
    <string name="azm_slot_label">Outer ring (Zone Minutes)</string>
    <string name="colors_label">Colors</string>
    <string name="font_label">Font</string>
    <string name="layout_label">Layout</string>
{toggles}
{layouts}
{fonts}
{lines}
</resources>
"""


def watchface():
    scene = "\n\n".join([
        background(),
        ring_slot(1, "azm_slot_label",
                  "com.fitbit.FitbitMobile/com.google.android.wearable.fitbit.mainapp.complications.offloadable.azm.OffloadableAZMComplicationDataSourceService",
                  *RING_AZM, 8, ACCENT, 31, 0, ACCENT,
                  "Outer ring + left number: Active Zone Minutes (Fitbit) by default", C, "showAzm", 12, 1, 45),
        ring_slot(0, "mysteps_slot_label",
                  "com.adrianp.mysteps/com.adrianp.mysteps.complication.HourlyStepsComplicationService",
                  *RING_STEPS, 0, MAIN, 20, 2, ACCENT,
                  "Middle ring + right number: MySteps, steps this hour", RING_STEPS[0] + RING_STEPS[1] / 2 + 1, "showSteps", 10, 50, 30, full_at_max_one=True),
        heart_rate(),
        seconds_dot(),
        per_font(date),
        per_style(time),
        weather(),
        "<!-- Taps on the time / heart open the big live pulse -->\n" + per_style(heart_taps),
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
    <ListConfiguration id="font" displayName="font_label" screenReaderText="font_label" defaultValue="{FAMILIES[0][0]}">
{indent(chr(10).join(f'<ListOption id="{fid}" displayName="font_{fid}" screenReaderText="font_{fid}" />' for fid, _ in FAMILIES), 6)}
    </ListConfiguration>
    <ListConfiguration id="layout" displayName="layout_label" screenReaderText="layout_label" defaultValue="{LAYOUTS[0][0]}">
{indent(chr(10).join(f'<ListOption id="{lid}" displayName="layout_{lid}" screenReaderText="layout_{lid}" />' for lid, _ in LAYOUTS), 6)}
    </ListConfiguration>
{indent(chr(10).join(f'<BooleanConfiguration id="{tid}" displayName="{tid}_label" screenReaderText="{tid}_label" defaultValue="TRUE" />' for tid, _ in TOGGLES), 4)}
  </UserConfigurations>

  <Scene backgroundColor="#ff000000">
{indent(scene, 4)}
  </Scene>
</WatchFace>
"""


if __name__ == "__main__":
    # Generated XML without indentation (res/raw is not compiled; it loads faster)
    OUT.write_text("\n".join(line.strip() for line in watchface().split("\n") if line.strip()) + "\n")
    (RES / "values/strings.xml").write_text(strings())
    print(f"wrote {OUT}", "columns:", [round(c, 1) for c in cols()])
