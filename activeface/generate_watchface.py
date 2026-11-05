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
# Customize → Colors: pink text with blue icons, or the two swapped
# Customize → Colors: (option id, label, text color, icon color); the first is the default
PINK_C, BLUE_C = "#ffce7fb3", "#ff2993ad"
COLOR_OPTIONS = [
    ("pink", "Pink & blue", PINK_C, BLUE_C),
    # Fitbit Inspire 3 palette (no official hex values exist; approximated from the
    # band colors, Fitbit's brand teal and the Active Zone Minutes colors)
    ("morning", "Morning Glow", "#fff7d58b", "#ffff9a6b"),
    ("lilac", "Lilac Bliss", "#ffc9b6ec", "#ff9b84d6"),
    ("midnight", "Midnight Zen", "#ffe2e2e2", "#ff6f7f9e"),
    ("teal", "Fitbit Teal", "#ff39cccc", "#ffe2e2e2"),
    ("azm", "Zone Minutes", "#fff8c33c", "#fff57c3a"),
]
PINK = "[CONFIGURATION.themeColor.0]"    # text, HR marker, always-on outline
BLUE = "#ff7092ea"
ICON = "[CONFIGURATION.themeColor.1]"
HEART = "#ffff3029"             # heart-rate heart: red, like the ❤ emoji

# Horseshoe rings: 280° from 220° (bottom-left) clockwise to 140° (bottom-right)
ARC_START, ARC_SWEEP = 220, 280

# Customize → shape options: (id, label). The first is the default (the Google layout)
TIME_SHAPES = [("pill", "Pill"), ("rounded", "Rounded box"), ("outline", "Outline"), ("none", "None")]
RING_STYLES = [("horseshoe", "Open"), ("full", "Full circle")]
RING_ANGLES = {"horseshoe": (ARC_START, ARC_SWEEP), "full": (0, 360)}
CIRCLE_STYLES = [("filled", "Filled"), ("outline", "Outline"), ("none", "None")]
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


def arc(cx, cy, r, stroke, color, end_expr=None, extra="", ring="horseshoe"):
    """Ring arc on mid-radius r; end_expr = fraction 0..1 of the sweep (None = whole ring)."""
    start, total = RING_ANGLES[ring]
    sweep = f"{start} + ({end_expr}) * {total}" if end_expr else None
    x, y, box = int_box(cx, cy, stroke + 2 * r)
    transform = f'\n    <Transform target="endAngle" value="{sweep}" />' if sweep else ""
    return f"""<PartDraw x="{x}" y="{y}" width="{box}" height="{box}"{extra}>
  <Arc centerX="{cx - x:g}" centerY="{cy - y:g}" width="{2 * r:g}" height="{2 * r:g}" startAngle="{start}" endAngle="{start + total}">{transform}
    <Stroke color="{color}" thickness="{stroke}" cap="ROUND" />
  </Arc>
</PartDraw>"""


def options(config_id, variants, w=SIZE, h=SIZE):
    """ListConfiguration: one Group per option id (variants: {id: xml})."""
    opts = "\n".join(f"""<ListOption id="{oid}">
  <Group x="0" y="0" width="{w}" height="{h}" name="{config_id}_{oid}">
{indent(xml, 4)}
  </Group>
</ListOption>""" for oid, xml in variants.items())
    return f"""<ListConfiguration id="{config_id}">
{indent(opts, 2)}
</ListConfiguration>"""


def ring_disc(cx, cy, d, color, style, stroke=3):
    """Circle background: filled, outlined or nothing."""
    if style == "filled":
        return disc(cx, cy, d, color)
    if style == "none":
        return "<!-- no background -->"
    x, y, box = int_box(cx, cy, d)
    return f"""<PartDraw x="{x}" y="{y}" width="{box}" height="{box}">
  <Ellipse x="{cx - d / 2 - x + stroke / 2:g}" y="{cy - d / 2 - y + stroke / 2:g}" width="{d - stroke:g}" height="{d - stroke:g}">
    <Stroke color="{PINK}" thickness="{stroke}" />
  </Ellipse>
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

    size = round(d + 1)

    def progress(fraction, ring):
        # A zero-length arc would still draw a round cap: hide it at 0
        return arc(lc(cx), lcy(cy), r, stroke, BLUE, fraction, ring=ring).replace(
            "\n  <Arc", f'\n  <Transform target="alpha" value="({fraction}) &gt; 0 ? 255 : 0" />\n  <Arc', 1)

    inner = r - stroke / 2

    def content(ring):
        """Text and icon; with a full ring they move up into the circle, off the ring."""
        if ring == "full":
            t_dy, i_dy = -0.2 * inner, inner - icon_box / 2 - 4
        else:
            t_dy, i_dy = text_dy, icon_dy
        label_text = text(template("[COMPLICATION.TEXT]"), lc(cx), lcy(cy + t_dy), text_size,
                          width=round(2 * r - stroke - 6), auto=True)
        ix, iy = round(lc(cx) - icon_box / 2), round(lcy(cy + i_dy) - icon_box / 2)
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
        return [label_text, icon]

    def rings(fraction=None, with_content=True):
        """Ring track (+ progress) and content for each Customize → Rings option."""
        variants = {
            ring: "\n".join([arc(lc(cx), lcy(cy), r, stroke, NAVY, ring=ring)]
                            + ([progress(fraction, ring)] if fraction else [])
                            + (content(ring) if with_content else []))
            for ring, _ in RING_STYLES}
        # Complications only take parts, groups and conditions: wrap the option list
        return f"""<Group x="0" y="0" width="{size}" height="{size}" name="Rings">
{indent(options("rings", variants, size, size), 2)}
</Group>"""

    def body(kind, *parts):
        return f"""<Complication type="{kind}">
{indent(chr(10).join(parts), 2)}
</Complication>"""

    return f"""<!-- {comment} -->
<ComplicationSlot x="{ox}" y="{oy}" width="{size}" height="{size}" slotId="{slot_id}"
    displayName="{label}" supportedTypes="RANGED_VALUE GOAL_PROGRESS SHORT_TEXT EMPTY">
  <DefaultProviderPolicy
      primaryProvider="{provider}"
      primaryProviderType="RANGED_VALUE"
      defaultSystemProvider="EMPTY"
      defaultSystemProviderType="EMPTY" />
  <BoundingOval x="0" y="0" width="{size}" height="{size}" />
{indent(body("RANGED_VALUE", rings(RANGED)), 2)}
{indent(body("GOAL_PROGRESS", rings(GOAL)), 2)}
{indent(body("SHORT_TEXT", rings()), 2)}
{indent(body("EMPTY", rings(with_content=False)), 2)}
</ComplicationSlot>"""


def heart_rate():
    return options("rings", {ring: heart_rate_ring(ring) for ring, _ in RING_STYLES})


def heart_rate_ring(ring):
    cx, cy, outer, stroke = 368.5, 223.5, 78.5, 20
    r = outer - stroke / 2
    start, total = RING_ANGLES[ring]
    theta = f"rad({start} + clamp([HEART_RATE] / {HR_MAX}, 0, 1) * {total})"
    marker = f"""<Group x="0" y="0" width="34" height="34" name="HrMarker">
  <Transform target="x" value="{cx} + {r} * sin({theta}) - 17" />
  <Transform target="y" value="{cy} - {r} * cos({theta}) - 17" />
{indent(disc(17, 17, 33, "#ff000000"), 2)}
{indent(disc(17, 17, 19, PINK), 2)}
</Group>"""
    # Full ring: number and heart move up so the heart clears the ring's bottom
    ny, hy = (cy - 8, cy + 30) if ring == "full" else (cy + 1.5, 281)
    number = text(template("round([HEART_RATE])"), cx, ny, 52, width=120)
    dashes = text("--", cx, ny, 52, width=120)
    return f"""<!-- Heart rate: blue ring with a marker at the current bpm, number, heart -->
{arc(cx, cy, r, stroke, BLUE, ring=ring)}
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
{image("ic_heart", round(cx - 18), round(hy - 16), 36, 32, tint=HEART)}"""


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
{options("circles", {st: ring_disc(cx, cy, 104, NAVY, st) for st, _ in CIRCLE_STYLES})}
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
{options("circles", {st: ring_disc(cx, cy, 129, NAVY, st) for st, _ in CIRCLE_STYLES})}
{text(template("[DAY_Z]"), cx, cy - 14.5, 41, width=120)}
{text(month, cx + 1, cy + 20, 26, font="gs_bold_wide", width=120)}"""


def time_box(shape, ambient):
    """Background of the time for one shape; ambient draws outlines only."""
    if shape == "none":
        return "<!-- no box -->"
    radius = 24 if shape == "rounded" else 55.5
    if ambient or shape == "outline":
        variant = "" if shape == "outline" else f"\n  {AMBIENT_SHOW}"
        alpha = "" if shape == "outline" else ' alpha="0"'
        return f"""<PartDraw x="6" y="171" width="262" height="115"{alpha}>{variant}
  <RoundRectangle x="1.5" y="1.5" width="259" height="112" cornerRadiusX="{radius + 0.5:g}" cornerRadiusY="{radius + 0.5:g}">
    <Stroke color="{PINK}" thickness="3" />
  </RoundRectangle>
</PartDraw>"""
    return f"""<PartDraw x="8" y="173" width="258" height="111">
  {AMBIENT_HIDE}
  <RoundRectangle x="0" y="0" width="258" height="111" cornerRadiusX="{radius:g}" cornerRadiusY="{radius:g}">
    <Fill color="{NAVY}" />
  </RoundRectangle>
</PartDraw>"""


def time():
    boxes = {shape: "\n".join(dict.fromkeys([time_box(shape, False), time_box(shape, True)]))
             for shape, _ in TIME_SHAPES}
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
    return f"""<!-- Time in a box (Customize → Time shape; outlined, thinner digits in always-on) -->
{options("timeShape", boxes)}
{clock("gs_time", AMBIENT_HIDE)}
{clock("gs_time_ambient", AMBIENT_SHOW, ' alpha="0"')}"""


def color_option(option):
    oid, _, text_color, icon_color = option
    return (f'<ColorOption id="{oid}" displayName="colors_{oid}" screenReaderText="colors_{oid}"\n'
            f'    colors="{text_color} {icon_color}" />')


def list_config(config_id, prefix, items):
    opts = "\n".join(f'  <ListOption id="{oid}" displayName="{prefix}_{oid}" screenReaderText="{prefix}_{oid}" />'
                     for oid, _ in items)
    return f"""<ListConfiguration id="{config_id}" displayName="{prefix}_label" screenReaderText="{prefix}_label" defaultValue="{items[0][0]}">
{opts}
</ListConfiguration>"""


def strings():
    """values/strings.xml: slot names and the color option labels."""
    entries = [(f"colors_{oid}", label) for oid, label, _, _ in COLOR_OPTIONS]
    for prefix, items in (("time", TIME_SHAPES), ("rings", RING_STYLES), ("circles", CIRCLE_STYLES)):
        entries += [(f"{prefix}_{oid}", label) for oid, label in items]
    lines = "\n".join(f'    <string name="{name}">{label.replace("&", "&amp;")}</string>'
                      for name, label in entries)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!-- GENERATED by activeface/generate_watchface.py -->
<resources>
    <string name="watch_face_name">MySteps Active</string>
    <string name="mysteps_slot_label">MySteps</string>
    <string name="azm_slot_label">Top left</string>
    <string name="colors_label">Colors</string>
    <string name="time_label">Time shape</string>
    <string name="rings_label">Rings</string>
    <string name="circles_label">Circles</string>
{lines}
</resources>
"""


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

  <UserConfigurations>
    <ColorConfiguration id="themeColor" displayName="colors_label" defaultValue="{COLOR_OPTIONS[0][0]}">
{indent(chr(10).join(color_option(o) for o in COLOR_OPTIONS), 6)}
    </ColorConfiguration>
{indent(list_config("timeShape", "time", TIME_SHAPES), 4)}
{indent(list_config("rings", "rings", RING_STYLES), 4)}
{indent(list_config("circles", "circles", CIRCLE_STYLES), 4)}
  </UserConfigurations>

  <Scene backgroundColor="#ff000000">
{indent(scene, 4)}
  </Scene>
</WatchFace>
"""


if __name__ == "__main__":
    OUT.write_text(watchface())
    (OUT.parent.parent / "values/strings.xml").write_text(strings())
    print(f"wrote {OUT}")
