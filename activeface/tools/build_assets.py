#!/usr/bin/env python3
"""Builds the fonts and icons in src/main/res from upstream sources.

    python3 activeface/tools/build_assets.py <GoogleSansFlex[...].ttf> <material-symbols-svg-dir>

Fonts: static instances of Google Sans Flex (OFL, github.com/google/fonts ofl/googlesansflex),
rounded (ROND=100), subset to Latin. Weights/widths/sizes were fitted to screenshots.
Icons: Material Symbols Rounded, filled (Apache 2.0), rendered with rsvg-convert and
trimmed to the glyph so the generator can place them by their visible bounds.
"""
import subprocess, sys, tempfile
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools import subset

RES = Path(__file__).resolve().parent.parent / "src/main/res"
FONTS = {  # name: (wght, wdth, opsz)
    "gs_time": (650, 100, 80),
    "gs_time_ambient": (500, 100, 80),
    "gs_bold": (650, 100, 36),
    "gs_bold_wide": (650, 110, 36),
}
WHITE = "#ffffff"  # tinted in the watch face
ICONS = {  # resource: (symbol, flip horizontally)
    "ic_heart": ("favorite", False),
    "ic_wx_sunny": ("sunny", False),
    "ic_wx_night": ("bedtime", False),
    "ic_wx_partly_day": ("partly_cloudy_day", False),
    "ic_wx_partly_night": ("partly_cloudy_night", False),
    "ic_wx_cloud": ("cloud", False),
    "ic_wx_fog": ("foggy", False),
    "ic_wx_rain": ("rainy", False),
    "ic_wx_snow": ("weather_snowy", False),
    "ic_wx_storm": ("thunderstorm", False),
    "ic_wx_wind": ("air", False),
}


def fonts(src):
    for name, (wght, wdth, opsz) in FONTS.items():
        f = instancer.instantiateVariableFont(
            TTFont(src), {"wght": wght, "wdth": wdth, "opsz": opsz, "ROND": 100, "slnt": 0})
        opts = subset.Options()
        opts.layout_features = ["*"]
        opts.name_IDs = ["*"]
        opts.glyph_names = True
        s = subset.Subsetter(opts)
        s.populate(glyphs=["colon.time"], unicodes=list(range(0x20, 0x7F)) + list(range(0xA0, 0x180)) + [0x2026, 0x2013, 0x2014])
        s.subset(f)
        if name.startswith("gs_time"):
            # The plain colon sits on the baseline; colon.time is centered on the digits
            for table in f["cmap"].tables:
                if 0x3A in table.cmap:
                    table.cmap[0x3A] = "colon.time"
        f.save(RES / "font" / f"{name}.ttf")


def icons(svg_dir):
    from PIL import Image
    for res, (sym, flip) in ICONS.items():
        svg = (Path(svg_dir) / f"{sym}.svg").read_text().replace("<path ", f'<path fill="{WHITE}" ')
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "i.svg"; p.write_text(svg); png = Path(d) / "i.png"
            subprocess.run(["rsvg-convert", "-w", "192", "-h", "192", str(p), "-o", str(png)], check=True)
            im = Image.open(png).convert("RGBA")
        if flip:
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
        im = im.crop(im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox())
        im.save(RES / "drawable" / f"{res}.png")
        print(res, im.size)


if __name__ == "__main__":
    fonts(sys.argv[1])
    icons(sys.argv[2])
