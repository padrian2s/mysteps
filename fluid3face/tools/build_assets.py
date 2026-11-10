#!/usr/bin/env python3
"""Builds the fonts and hand images in src/main/res for the Fluid v3 watch face:

    python3 fluid3face/tools/build_assets.py <Jost[wght].ttf>

Fonts: Jost (OFL, github.com/google/fonts ofl/jost), static weights subset to Latin +
Romanian, with tabular digits baked into the cmap (the design uses tabular-nums, which
WFF can't request). jost_time (bold, asked on the watch) also carries the design's -0.02 em tracking in its digit
advances (TimeText takes no letterSpacing).

Hands: the design's short dauphine hands (two facets, one lit and one shaded, pointed
tip), drawn 4x and downsampled, with the drop shadow baked in.
"""
import math
import sys
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools import subset
from PIL import Image, ImageDraw, ImageFilter

RES = Path(__file__).resolve().parent.parent / "src/main/res"
FONTS = {"jost_extralight": 200, "jost_light": 300, "jost_regular": 400, "jost_time": 700,
         "jost_time_strong": 760, "jost_time_vstrong": 830, "jost_time_ultra": 900}
TIME_TRACKING = -20          # -0.02 em at 1000 units per em
UNICODES = (list(range(0x20, 0x7F)) + list(range(0xA0, 0x180))
            + [0x218, 0x219, 0x21A, 0x21B, 0x2026, 0x2013, 0x2014, 0x2022])

K = 456 / 450                # design px -> watch px
# (name, base radius, tip radius, width, belly) in design px; normal is the mock-up's,
# small and large are the Customize → Hands options
HANDS = [("hand_hour_small", 188, 205, 8, 0.38), ("hand_minute_small", 190, 223, 5, 0.26),
         ("hand_hour_normal", 178, 205, 11, 0.38), ("hand_minute_normal", 178, 223, 7, 0.26),
         ("hand_hour_large", 160, 205, 15, 0.38), ("hand_minute_large", 155, 223, 10, 0.26)]
LIGHT, SHADE = (0xF8, 0xEE, 0xD6, 255), (0xB8, 0x9A, 0x5C, 255)
PAD = 3                      # watch px of room around the hand for its shadow


def tnum_map(font):
    gsub = font["GSUB"].table
    out = {}
    for rec in gsub.FeatureList.FeatureRecord:
        if rec.FeatureTag != "tnum":
            continue
        for li in rec.Feature.LookupListIndex:
            for st in gsub.LookupList.Lookup[li].SubTable:
                st = getattr(st, "ExtSubTable", st)
                out.update(getattr(st, "mapping", {}))
    return out


def build_fonts(src):
    for name, wght in FONTS.items():
        f = instancer.instantiateVariableFont(TTFont(src), {"wght": wght})
        tnum = tnum_map(f)
        for table in f["cmap"].tables:
            for cp, glyph in list(table.cmap.items()):
                if glyph in tnum:
                    table.cmap[cp] = tnum[glyph]
        opts = subset.Options()
        opts.layout_features = ["kern", "liga", "ccmp", "locl"]
        opts.name_IDs = ["*"]
        s = subset.Subsetter(opts)
        s.populate(unicodes=UNICODES)
        s.subset(f)
        if name.startswith("jost_time"):
            hm, cm = f["hmtx"], f.getBestCmap()
            for glyph in {cm[c] for c in range(0x30, 0x3A)}:
                adv, lsb = hm[glyph]
                hm[glyph] = (adv + TIME_TRACKING, lsb)
        f.save(RES / "font" / f"{name}.ttf")
        print(name, "digit advance", f["hmtx"][f.getBestCmap()[ord("0")]][0])


def build_hands():
    """Image from the dial center (bottom edge, the pivot) up to the tip, plus PAD."""
    ss = 4
    for name, r0, r1, w, belly in HANDS:
        width = 2 * math.ceil((w * K + 2 * PAD) / 2)   # even, so the hand sits on the pivot
        height = r1 * K + PAD
        W, H = round(width * ss), round(height * ss)
        cx = W / 2
        y0, y1 = H - r0 * K * ss, H - r1 * K * ss
        ym = H - (r0 + (r1 - r0) * belly) * K * ss
        half = w * K * ss / 2
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        # drop-shadow(0 1px 2px rgba(0,0,0,.7))
        shadow = Image.new("L", (W, H), 0)
        ImageDraw.Draw(shadow).polygon([(cx, y0 + ss), (cx - half, ym + ss), (cx, y1 + ss),
                                        (cx + half, ym + ss)], fill=178)
        shadow = shadow.filter(ImageFilter.GaussianBlur(2 * K * ss / 2))
        img.paste((0, 0, 0, 255), (0, 0), shadow)
        d = ImageDraw.Draw(img)
        d.polygon([(cx, y0), (cx - half, ym), (cx, y1)], fill=LIGHT)
        d.polygon([(cx, y0), (cx + half, ym), (cx, y1)], fill=SHADE)
        img = img.resize((round(width), round(height)), Image.LANCZOS)
        img.save(RES / "drawable" / f"{name}.png")
        print(name, img.size)


if __name__ == "__main__":
    build_fonts(sys.argv[1])
    build_hands()
