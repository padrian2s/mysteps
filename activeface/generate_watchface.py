#!/usr/bin/env python3
"""Generates src/main/res/raw/watchface.xml for the Active watch face.

Edit this file, not the XML:

    python3 activeface/generate_watchface.py

The layout copies the Google "Active" face as shown on a Pixel Watch 3 (456 px):
positions, radii, stroke widths, colors and font sizes were measured from screenshots.
Unlike the original, this face is drawn by the watch's main processor in always-on
too (Watch Face Format faces with TimeText can't be handed to the low-power chip), so
raising the wrist wakes Android and MySteps refreshes its complication immediately.
"""
from pathlib import Path

OUT = Path(__file__).parent / "src/main/res/raw/watchface.xml"

SIZE = 456
NAVY = "#ff161d2f"
PINK = "#ffce7fb3"
BLUE = "#ff7092ea"
ICON = "#ff30adcc"              # icons: light blue
HEART = "#ffff3029"             # heart-rate heart: red, like the ❤ emoji

# Horseshoe rings: 280° from 220° (bottom-left) clockwise to 140° (bottom-right)
ARC_START, ARC_SWEEP = 220, 280
HR_MAX = 175                    # heart-rate ring spans 0..175 bpm (fitted to screenshots)

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

AMBIENT_HIDE = '<Variant mode="AMBIENT" target="alpha" value="0" />'
AMBIENT_SHOW = '<Variant mode="AMBIENT" target="alpha" value="255" />'

# Text is centered on its cap height: WFF centers the font's line box, so shift the
# box by this fraction of the font size to put the digits' middle on the given y
CAP_SHIFT = 0.0


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


def text(content, cx, cy, size, font="gs_bold", color=PINK, width=None, extra="", auto=False):
    """Single-line text centered on (cx, cy); auto shrinks it to fit the width."""
    w = width or SIZE
    h = round(size * 1.6)
    y = round(cy - h / 2 + CAP_SHIFT * size)
    return f"""<PartText x="{round(cx - w / 2)}" y="{y}" width="{w}" height="{h}"{extra}>
  <Text align="CENTER"{' isAutoSize="TRUE"' if auto else ''}>
    <Font family="{font}" size="{size}" color="{color}">{content}</Font>
  </Text>
</PartText>"""


def template(expr, fmt="%s"):
    return f'<Template>{fmt}<Parameter expression="{expr}" /></Template>'


def image(resource, x, y, w, h, extra="", tint=None):
    t = f' tintColor="{tint}"' if tint else ""
    return f"""<PartImage x="{x}" y="{y}" width="{w}" height="{h}"{t}{extra}>
  <Image resource="{resource}" />
</PartImage>"""


def arc(cx, cy, r, stroke, color, end_expr=None, extra=""):
    """Horseshoe arc on mid-radius r; end_expr = fraction 0..1 of the sweep (None = full)."""
    sweep = f"{ARC_START} + ({end_expr}) * {ARC_SWEEP}" if end_expr else None
    x, y, box = int_box(cx, cy, stroke + 2 * r)
    transform = f'\n    <Transform target="endAngle" value="{sweep}" />' if sweep else ""
    return f"""<PartDraw x="{x}" y="{y}" width="{box}" height="{box}"{extra}>
  <Arc centerX="{cx - x:g}" centerY="{cy - y:g}" width="{2 * r:g}" height="{2 * r:g}" startAngle="{ARC_START}" endAngle="{ARC_START + ARC_SWEEP}">{transform}
    <Stroke color="{color}" thickness="{stroke}" cap="ROUND" />
  </Arc>
</PartDraw>"""


def int_box(cx, cy, d):
    """Integer square (Parts need integer bounds) holding a d-wide shape centered on cx, cy."""
    import math
    x, y = math.floor(cx - d / 2), math.floor(cy - d / 2)
    return x, y, math.ceil(max(cx + d / 2 - x, cy + d / 2 - y))


def disc(cx, cy, d, color, extra=""):
    x, y, box = int_box(cx, cy, d)
    return f"""<PartDraw x="{x}" y="{y}" width="{box}" height="{box}"{extra}>
  <Ellipse x="{cx - d / 2 - x:g}" y="{cy - d / 2 - y:g}" width="{d:g}" height="{d:g}">
    <Fill color="{color}" />
  </Ellipse>
</PartDraw>"""


RANGED = ("(clamp([COMPLICATION.RANGED_VALUE_VALUE], [COMPLICATION.RANGED_VALUE_MIN], "
          "[COMPLICATION.RANGED_VALUE_MAX]) - [COMPLICATION.RANGED_VALUE_MIN]) / "
          "([COMPLICATION.RANGED_VALUE_MAX] - [COMPLICATION.RANGED_VALUE_MIN])")
GOAL = "clamp([COMPLICATION.GOAL_PROGRESS_VALUE] / [COMPLICATION.GOAL_PROGRESS_TARGET_VALUE], 0, 1)"


def ring_complication(slot_id, cx, cy, outer, stroke, label, provider, text_size, text_dy,
                      icon_box, icon_dy, comment):
    """Ring complication: navy horseshoe track, blue progress, pink text, yellow icon."""
    r = outer - stroke / 2
    d = 2 * outer
    ox, oy = int(cx - outer), int(cy - outer)  # slot origin; children are slot-relative
    lc = lambda v: v - ox                     # local x
    lcy = lambda v: v - oy                    # local y

    def progress(fraction):
        # A zero-length arc would still draw a round cap: hide it at 0
        return arc(lc(cx), lcy(cy), r, stroke, BLUE, fraction,
                   extra="").replace("<PartDraw ", "<PartDraw ", 1).replace(
            "\n  <Arc", f'\n  <Transform target="alpha" value="({fraction}) &gt; 0 ? 255 : 0" />\n  <Arc', 1)

    track = arc(lc(cx), lcy(cy), r, stroke, NAVY)
    label_text = text(template("[COMPLICATION.TEXT]"), lc(cx), lcy(cy + text_dy), text_size,
                      width=round(2 * r - stroke - 6), auto=True)
    ix, iy = round(lc(cx) - icon_box / 2), round(lcy(cy + icon_dy) - icon_box / 2)
    # Solid color through the icon's shape: providers may send colored "monochromatic"
    # icons (Fitbit's AZM one is orange), and tintColor multiplies instead of replacing
    icon = f"""<Group x="{ix}" y="{iy}" width="{icon_box}" height="{icon_box}" name="Icon">
  <PartDraw x="0" y="0" width="{icon_box}" height="{icon_box}">
    <Rectangle x="0" y="0" width="{icon_box}" height="{icon_box}">
      <Fill color="{ICON}" />
    </Rectangle>
  </PartDraw>
{indent(image("[COMPLICATION.MONOCHROMATIC_IMAGE]", 0, 0, icon_box, icon_box, extra=' renderMode="MASK"'), 2)}
</Group>"""

    def body(kind, *parts):
        return f"""<Complication type="{kind}">
{indent(chr(10).join(parts), 2)}
</Complication>"""

    return f"""<!-- {comment} -->
<ComplicationSlot x="{ox}" y="{oy}" width="{round(d + 1)}" height="{round(d + 1)}" slotId="{slot_id}"
    displayName="{label}" supportedTypes="RANGED_VALUE GOAL_PROGRESS SHORT_TEXT EMPTY">
  <DefaultProviderPolicy
      primaryProvider="{provider}"
      primaryProviderType="RANGED_VALUE"
      defaultSystemProvider="EMPTY"
      defaultSystemProviderType="EMPTY" />
  <BoundingOval x="0" y="0" width="{round(d + 1)}" height="{round(d + 1)}" />
{indent(body("RANGED_VALUE", track, progress(RANGED), label_text, icon), 2)}
{indent(body("GOAL_PROGRESS", track, progress(GOAL), label_text, icon), 2)}
{indent(body("SHORT_TEXT", track, label_text, icon), 2)}
{indent(body("EMPTY", track), 2)}
</ComplicationSlot>"""


def heart_rate():
    cx, cy, outer, stroke = 368.5, 223.5, 78.5, 20
    r = outer - stroke / 2
    theta = f"rad({ARC_START} + clamp([HEART_RATE] / {HR_MAX}, 0, 1) * {ARC_SWEEP})"
    marker = f"""<Group x="0" y="0" width="34" height="34" name="HrMarker">
  <Transform target="x" value="{cx} + {r} * sin({theta}) - 17" />
  <Transform target="y" value="{cy} - {r} * cos({theta}) - 17" />
{indent(disc(17, 17, 33, "#ff000000"), 2)}
{indent(disc(17, 17, 19, PINK), 2)}
</Group>"""
    number = text(template("round([HEART_RATE])"), cx, cy + 1.5, 52, width=120)
    dashes = text("--", cx, cy + 1.5, 52, width=120)
    return f"""<!-- Heart rate: blue ring with a marker at the current bpm, number, heart -->
{arc(cx, cy, r, stroke, BLUE)}
<Condition>
  <Expressions>
    <Expression name="hasHr">[HEART_RATE] &gt; 0</Expression>
  </Expressions>
  <Compare expression="hasHr">
{indent(marker, 4)}
{indent(number, 4)}
  </Compare>
  <Default>
{indent(dashes, 4)}
  </Default>
</Condition>
{image("ic_heart", 350, 265, 36, 32, tint=HEART)}"""


WEATHER_ICONS = [  # (WEATHER.CONDITION values, day icon, night icon)
    ((1, 8), "ic_wx_sunny", "ic_wx_night"),
    ((14,), "ic_wx_partly_day", "ic_wx_partly_night"),
    ((2,), "ic_wx_cloud", "ic_wx_cloud"),
    ((3, 13), "ic_wx_fog", "ic_wx_fog"),
    ((4, 6, 12), "ic_wx_rain", "ic_wx_rain"),
    ((5, 7, 10, 11), "ic_wx_snow", "ic_wx_snow"),
    ((9,), "ic_wx_storm", "ic_wx_storm"),
    ((15,), "ic_wx_wind", "ic_wx_wind"),
]
ICON_SIZES = {  # trimmed PNG sizes (tools/build_assets.py), for the aspect ratio
    "ic_wx_sunny": (176, 176), "ic_wx_night": (113, 160), "ic_wx_partly_day": (168, 153),
    "ic_wx_partly_night": (166, 157), "ic_wx_cloud": (176, 128), "ic_wx_fog": (160, 160),
    "ic_wx_rain": (160, 161), "ic_wx_snow": (160, 168), "ic_wx_storm": (160, 176),
    "ic_wx_wind": (160, 136),
}
WEATHER_ICON_BOX = 74             # fills the 104 px circle
WEATHER_ICON_ALPHA = 90           # faint, so the temperature on top stays readable


def weather_icon(res, cx, cy):
    iw, ih = ICON_SIZES[res]
    k = WEATHER_ICON_BOX / max(iw, ih)
    w, h = round(iw * k), round(ih * k)
    return image(res, round(cx - w / 2), round(cy - h / 2), w, h,
                 extra=f' alpha="{WEATHER_ICON_ALPHA}"', tint=ICON)


def weather():
    """Big condition icon across the circle, temperature in the middle."""
    cx, cy = 130, 350
    exprs, compares = [], []
    for i, (conds, day, night) in enumerate(WEATHER_ICONS):
        cond = " || ".join(f"[WEATHER.CONDITION] == {c}" for c in conds)
        exprs.append(f'<Expression name="day{i}">[WEATHER.IS_AVAILABLE] &amp;&amp; [WEATHER.IS_DAY] &amp;&amp; ({cond})</Expression>')
        exprs.append(f'<Expression name="night{i}">[WEATHER.IS_AVAILABLE] &amp;&amp; ({cond})</Expression>')
        compares.append(f'<Compare expression="day{i}">\n{indent(weather_icon(day, cx, cy), 2)}\n</Compare>')
        compares.append(f'<Compare expression="night{i}">\n{indent(weather_icon(night, cx, cy), 2)}\n</Compare>')
    temp = text(template("[WEATHER.TEMPERATURE]", "%s°"), cx + 0.5, cy, 36, width=100)
    return f"""<!-- Weather: condition icon filling the circle, temperature in the middle -->
{disc(cx, cy, 104, NAVY)}
<Condition>
  <Expressions>
{indent(chr(10).join(exprs), 4)}
  </Expressions>
{indent(chr(10).join(compares), 2)}
</Condition>
<Condition>
  <Expressions>
    <Expression name="hasWeather">[WEATHER.IS_AVAILABLE]</Expression>
  </Expressions>
  <Compare expression="hasWeather">
{indent(temp, 4)}
  </Compare>
  <Default>
{indent(text("--", cx + 0.5, cy, 36, width=100), 4)}
  </Default>
</Condition>"""


def date():
    """Day of the month on top, short month below, centered as a block in the circle."""
    cx, cy = 276.5, 367.5
    month = template(chain("[MONTH]", [m + "." for m in MONTHS], quote=True))
    return f"""<!-- Date: day, then month -->
{disc(cx, cy, 129, NAVY)}
{text(template("[DAY_Z]"), cx, cy - 14.5, 41, width=120)}
{text(month, cx + 1, cy + 20, 26, font="gs_bold_wide", width=120)}"""


def time():
    pill = """<PartDraw x="8" y="173" width="258" height="111" name="TimePill">
  {hide}
  <RoundRectangle x="0" y="0" width="258" height="111" cornerRadiusX="55.5" cornerRadiusY="55.5">
    <Fill color="{navy}" />
  </RoundRectangle>
</PartDraw>
<!-- Always-on: outline only -->
<PartDraw x="6" y="171" width="262" height="115" alpha="0" name="TimePillAmbient">
  {show}
  <RoundRectangle x="1.5" y="1.5" width="259" height="112" cornerRadiusX="56" cornerRadiusY="56">
    <Stroke color="{pink}" thickness="3" />
  </RoundRectangle>
</PartDraw>""".format(hide=AMBIENT_HIDE, show=AMBIENT_SHOW, navy=NAVY, pink=PINK)
    cx, cy, size = 137, 230, 80
    h = round(size * 1.6)
    y = round(cy - h / 2 + CAP_SHIFT * size)

    def clock(font, variant, alpha=""):
        return f"""<DigitalClock x="{cx - 125}" y="{y}" width="250" height="{h}"{alpha}>
  {variant}
  <TimeText format="hh:mm" hourFormat="SYNC_TO_DEVICE" align="CENTER" x="0" y="0" width="250" height="{h}">
    <Font family="{font}" size="{size}" color="{PINK}" />
  </TimeText>
</DigitalClock>"""
    return f"""<!-- Time in a rounded pill (outlined, thinner digits in always-on) -->
{pill}
{clock("gs_time", AMBIENT_HIDE)}
{clock("gs_time_ambient", AMBIENT_SHOW, ' alpha="0"')}"""


def watchface():
    scene = "\n\n".join([
        ring_complication(1, 130, 106, 52, 12, "azm_slot_label",
                          "com.fitbit.FitbitMobile/com.google.android.wearable.fitbit.mainapp.complications.offloadable.azm.OffloadableAZMComplicationDataSourceService",
                          33, 0, 28, 37.5, "Top left: Active Zone Minutes (Fitbit) by default"),
        ring_complication(0, 276, 86.5, 64.5, 15, "mysteps_slot_label",
                          "com.adrianp.mysteps/com.adrianp.mysteps.complication.HourlyStepsComplicationService",
                          36, 0, 36, 46.5, "Top: MySteps, steps this hour (❤N/M once the goal is met)"),
        time(),
        heart_rate(),
        weather(),
        date(),
    ])
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!-- GENERATED by activeface/generate_watchface.py — edit that file, not this one. -->
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
    print(f"wrote {OUT}")
