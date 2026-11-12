#!/usr/bin/env python3
"""Builds the fonts in src/main/res/font from Space Grotesk and JetBrains Mono (both OFL,
github.com/google/fonts ofl/spacegrotesk and ofl/jetbrainsmono):

    python3 fluidface/tools/build_assets.py <SpaceGrotesk[wght].ttf> <JetBrainsMono[wght].ttf>

Static weights, subset to Latin + Romanian, with tabular digits baked into the cmap
(the design uses font-variant-numeric: tabular-nums, which WFF can't request).
sg_time also tightens the digits by -0.05 em (TimeText takes no letterSpacing).
"""
import sys
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools import subset

RES = Path(__file__).resolve().parent.parent / "src/main/res"
FONTS = {prefix + "_" + role: wght for prefix in ("sg", "jb")
         for role, wght in (("light", 300), ("medium", 500), ("time", 300))}
# TimeText has no letterSpacing: sg_time carries the design's -0.05 em in its digit advances
TIME_TRACKING = -50
UNICODES = (list(range(0x20, 0x7F)) + list(range(0xA0, 0x180))
            + [0x218, 0x219, 0x21A, 0x21B, 0x2026, 0x2013, 0x2014, 0x2022])


def tnum_map(font):
    """Glyph substitutions of the 'tnum' feature (single substitutions only)."""
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


def build(sources):
    for name, wght in FONTS.items():
        src = sources[name.split("_")[0]]
        f = instancer.instantiateVariableFont(TTFont(src), {"wght": wght})
        tnum = tnum_map(f) if "GSUB" in f else {}
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
        if name.endswith("_time"):
            hm, cm = f["hmtx"], f.getBestCmap()
            for glyph in {cm[c] for c in range(0x30, 0x3A)}:
                adv, lsb = hm[glyph]
                hm[glyph] = (adv + TIME_TRACKING, lsb)
        f.save(RES / "font" / f"{name}.ttf")
        cm, hm = f.getBestCmap(), f["hmtx"]
        print(name, {c: hm[cm[ord(c)]][0] for c in "018:"}, f["head"].unitsPerEm,
              f["OS/2"].sCapHeight, f["hhea"].ascent, f["hhea"].descent)


if __name__ == "__main__":
    build({"sg": sys.argv[1], "jb": sys.argv[2]})
