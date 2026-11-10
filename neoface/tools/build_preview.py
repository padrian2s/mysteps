#!/usr/bin/env python3
"""Renders src/main/res/drawable/preview.png (the watch face picker's image) from the
generator's own geometry and fonts, at the design's sample values (10:08, 77 zone
minutes of 150, 180 steps of 250, 89 bpm, 25°):

    python3 neoface/tools/build_preview.py
"""
import math
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import generate_watchface as g  # noqa: E402

SS = 4                      # supersampling
N = g.SIZE * SS


def P(v):
    return g.p(v) * SS


def S(v):
    return g.s(v) * SS


def rgb(c, a=1.0):
    return tuple(round(int(c[i:i + 2], 16) * a) for i in (3, 5, 7))


def main():
    im = Image.new("RGB", (N, N), "black")
    d = ImageDraw.Draw(im)
    c = N / 2

    def arc(r, w, col, a0, a1):
        """Round-capped arc on mid-radius r, degrees clockwise from 12 o'clock."""
        R, half = S(r), S(w) / 2
        d.arc([c - R - half, c - R - half, c + R + half, c + R + half], a0 - 90, a1 - 90,
              fill=col, width=round(S(w)))
        for a in (a0, a1):
            t = math.radians(a - 90)
            x, y = c + R * math.cos(t), c + R * math.sin(t)
            d.ellipse([x - half, y - half, x + half, y + half], fill=col)

    def font(name, size):
        return ImageFont.truetype(str(HERE / "src/main/res/font" / f"{name}.ttf"), round(S(size)))

    def text(t, x, y, name, size, col, anchor="mm", spacing=0.0):
        f = font(name, size)
        if not spacing:
            d.text((x, y), t, font=f, fill=col, anchor=anchor)
            return
        w = sum(f.getlength(ch) + S(size * spacing) for ch in t)
        x0 = {"mm": x - w / 2, "lm": x, "rm": x - w}[anchor]
        for ch in t:
            d.text((x0, y), ch, font=f, fill=col, anchor="lm")
            x0 += f.getlength(ch) + S(size * spacing)

    # Outer ring: 60 segments, 77 of 150 zone minutes lit, second 32 white
    lit = round(77 / 150 * 60)
    for i in range(60):
        col = rgb(g.INK) if i == 32 else rgb(g.VIOLET, 1 if i < lit else 0.18)
        arc(g.SEG_R, g.SEG_W, col, i * 6 - g.SEG_HALF, i * 6 + g.SEG_HALF)
    # Inner ring: 180 of 250 steps
    R, half = S(g.STEPS_R), S(g.STEPS_W) / 2
    d.ellipse([c - R - half, c - R - half, c + R + half, c + R + half],
              outline=rgb(g.LIME, 0.14), width=round(S(g.STEPS_W)))
    arc(g.STEPS_R, g.STEPS_W, rgb(g.LIME), 0, 360 * 180 / 250)

    # Time
    text("10", c, P(g.HOURS_CY), "unbounded_time", g.TIME_SIZE, rgb(g.INK))
    text("08", c, P(g.MINUTES_CY), "unbounded_time", g.TIME_SIZE, rgb(g.LIME))
    # Side columns
    for x, col, num, label in ((g.SIDE_LEFT_X, g.VIOLET, "77", "MIN"), (g.SIDE_RIGHT_X, g.LIME, "180", "PAȘI")):
        text(num, P(x), P(g.SIDE_NUM_CY), "unbounded_bold", g.SIDE_SIZE, rgb(col))
        text(label, P(x), P(g.SIDE_LABEL_CY), "inter_semibold", g.LABEL_SIZE, rgb(g.INK, 0.62),
             spacing=g.LABEL_SPACING)

    # Date pill
    dw = g.text_width("MIE 28 NOV", "inter_semibold", g.DATE_SIZE, g.DATE_SPACING)
    tw = g.text_width("25°", "inter_semibold", g.DATE_SIZE, g.DATE_SPACING)
    h = g.date_height()
    cy = g.DATE_TOP + h / 2
    w = 13 + dw + 8 + 3 + 8 + tw + 13 + 2
    d.rounded_rectangle([P(225 - w / 2), P(cy - h / 2), P(225 + w / 2), P(cy + h / 2)], radius=S(h / 2),
                        outline=rgb(g.INK, 0.24), width=round(S(1)))
    dot = 225 - w / 2 + 1 + 13 + dw + 8 + 1.5
    text("MAR 10 NOV", P(dot - 9.5), P(cy), "inter_semibold", g.DATE_SIZE, rgb(g.INK), "rm", g.DATE_SPACING)
    d.ellipse([P(dot - 1.5), P(cy - 1.5), P(dot + 1.5), P(cy + 1.5)], fill=rgb(g.INK, 0.5))
    text("25°", P(dot + 9.5), P(cy), "inter_semibold", g.DATE_SIZE, rgb(g.AMBER), "lm", g.DATE_SPACING)

    # Heart rate pill (rest zone)
    bw = g.text_width("89", "unbounded_bold", g.BPM_SIZE)
    lw = g.text_width("REPAUS", "inter_semibold", g.PILL_LABEL_SIZE, g.LABEL_SPACING)
    h = g.pill_height(1)
    cy = g.PILL_BOTTOM - h / 2
    w = 11 + g.PILL_HEART + 8 + bw + 8 + lw + 13
    x = 225 - w / 2 + 11
    d.rounded_rectangle([P(225 - w / 2), P(cy - h / 2), P(225 + w / 2), P(cy + h / 2)], radius=S(h / 2),
                        fill=rgb("#ff22242b"))
    heart = Image.open(HERE / "src/main/res/drawable/ic_heart.png").convert("RGBA")
    heart = heart.resize((round(S(g.PILL_HEART)), round(S(g.PILL_HEART * 0.89))), Image.LANCZOS)
    im.paste(Image.new("RGB", heart.size, rgb(g.RED)),
             (round(P(x)), round(P(cy - g.PILL_HEART * 0.89 / 2))), heart.split()[3])
    text("89", P(x + g.PILL_HEART + 8), P(cy), "unbounded_bold", g.BPM_SIZE, rgb(g.INK), "lm")
    text("REPAUS", P(x + g.PILL_HEART + 16 + bw), P(cy), "inter_semibold", g.PILL_LABEL_SIZE,
         rgb(g.INK, 0.8), "lm", g.LABEL_SPACING)

    mask = Image.new("L", (N, N), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, N, N], fill=255)
    out = Image.new("RGB", (N, N), "black")
    out.paste(im, (0, 0), mask)
    out.resize((g.SIZE, g.SIZE), Image.LANCZOS).save(HERE / "src/main/res/drawable/preview.png")
    print("wrote preview.png")


if __name__ == "__main__":
    main()
