#!/usr/bin/env python3
"""Builds the fonts in src/main/res/font for the Neo watch face:

    python3 neoface/tools/build_assets.py <Unbounded[wght].ttf> <Inter[opsz,wght].ttf>

Unbounded and Inter are OFL (github.com/google/fonts ofl/unbounded, ofl/inter). Static
weights, subset to Latin + Romanian, with tabular digits baked into the cmap (the
design uses tabular-nums, which WFF can't request). unbounded_time also carries the
design's -0.04 em tracking in its digit advances (TimeText takes no letterSpacing).
"""
import sys
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools import subset

RES = Path(__file__).resolve().parent.parent / "src/main/res"
# name: (source index, axes, digit tracking in font units)
FONTS = {"unbounded_time": (0, {"wght": 800}, -40),     # time, 800 as in the design
         "unbounded_bold": (0, {"wght": 700}, 0),       # zone minutes, steps, bpm
         "inter_semibold": (1, {"wght": 600, "opsz": 14}, 0)}  # date, labels
UNICODES = (list(range(0x20, 0x7F)) + list(range(0xA0, 0x180))
            + [0x218, 0x219, 0x21A, 0x21B, 0x2026, 0x2013, 0x2014, 0x2022])


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


def build_fonts(sources):
    for name, (src, axes, tracking) in FONTS.items():
        f = instancer.instantiateVariableFont(TTFont(sources[src]), axes)
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
        if tracking:
            hm, cm = f["hmtx"], f.getBestCmap()
            for glyph in {cm[c] for c in range(0x30, 0x3A)}:
                adv, lsb = hm[glyph]
                hm[glyph] = (adv + tracking, lsb)
        f.save(RES / "font" / f"{name}.ttf")
        print(name, "digit advance", f["hmtx"][f.getBestCmap()[ord("0")]][0])


if __name__ == "__main__":
    build_fonts(sys.argv[1:3])
