"""Measure the rendered rail from a browser screenshot.

Usage: python measure_rail.py <png> <clip_css_width> [label]
The clip was taken at x=0, so image x maps to CSS x as  x_css = x_img * clip_css_width / width_img.
"""
import sys
from collections import Counter

from PIL import Image

path = sys.argv[1]
clip_css_w = float(sys.argv[2])
label = sys.argv[3] if len(sys.argv) > 3 else path

im = Image.open(path).convert("RGB")
w, h = im.size
scale = w / clip_css_w
px = im.load()


def css(x):
    return x / scale


GREEN = (10, 70, 50)
strip_rows = []
for y in range(h):
    # the strip's right edge = last x where the pixel is green-ish
    edge = None
    for x in range(w):
        r, g, b = px[x, y]
        if abs(r - GREEN[0]) < 26 and abs(g - GREEN[1]) < 26 and abs(b - GREEN[2]) < 26:
            edge = x
    strip_rows.append(edge)

edge_counts = Counter(e for e in strip_rows if e is not None)
strip_edge_img = edge_counts.most_common(1)[0][0] if edge_counts else None

# glyph pixels: saturated / light pixels inside the strip that are not the green bg
glyph_cols = {}
for y in range(h):
    for x in range(0, (strip_edge_img or w) - 1):
        r, g, b = px[x, y]
        greenish = abs(r - GREEN[0]) < 30 and abs(g - GREEN[1]) < 30 and abs(b - GREEN[2]) < 30
        if not greenish:
            glyph_cols.setdefault(y // 6, []).append(x)

print("== %s ==" % label)
print("image %dx%d  scale %.4f px per css px" % (w, h, scale))
if strip_edge_img is not None:
    print("strip right edge: img %.0f -> css %.1f" % (strip_edge_img, css(strip_edge_img)))

# per 6-row band, the x-extent of non-green pixels (the glyphs)
bands = [(k, v) for k, v in sorted(glyph_cols.items())]
for k, v in bands:
    if len(v) < 3:
        continue
    lo, hi = min(v), max(v)
    if hi - lo < 4:
        continue
    print("band y=%3d..%3d  glyph css %5.1f -> %5.1f   (img %d..%d)"
          % (k * 6, k * 6 + 5, css(lo), css(hi), lo, hi))
