"""Measure the open rail: strip edge, glyph ink, and where the words start.

Usage: python measure_open.py <png> [css_width]
"""
import sys

from PIL import Image

path = sys.argv[1]
css_w = float(sys.argv[2]) if len(sys.argv) > 2 else None

im = Image.open(path).convert("RGB")
w, h = im.size
scale = (w / css_w) if css_w else 1.0
px = im.load()
GREEN = (10, 70, 50)


def near(c, t, tol=30):
    return abs(c[0] - t[0]) < tol and abs(c[1] - t[1]) < tol and abs(c[2] - t[2]) < tol


def is_green(c):
    return near(c, GREEN, 34)


def is_glyph(c):
    """a saturated colour that is not the green strip"""
    r, g, b = c
    return not is_green(c) and not (r > 230 and g > 230 and b > 230)


def is_text(c):
    """dark ink on white"""
    return sum(c) < 560 and not is_green(c)


# 1. strip edge: widest run of green on a row that has no glyph
strip_edge = 0
for y in range(h):
    x = 0
    while x < w and is_green(px[x, y]):
        x += 1
    strip_edge = max(strip_edge, x)

# 2. glyph ink columns in the strip (x < strip_edge)
glyph_rows = {}
for y in range(h):
    cols = [x for x in range(strip_edge) if is_glyph(px[x, y])]
    if cols:
        glyph_rows.setdefault(y // 6, []).extend(cols)

# 3. word ink: dark pixels to the right of the strip
word_cols = {}
for y in range(h):
    cols = [x for x in range(strip_edge + 2, min(w, strip_edge + 240))
            if is_text(px[x, y])]
    if cols:
        word_cols.setdefault(y // 6, []).extend(cols)


def band(rows, label, limit=None):
    print("-- %s --" % label)
    seen = 0
    for k, v in sorted(rows.items()):
        lo, hi = min(v), max(v)
        if hi - lo < 3:
            continue
        print("   band y=%3d  css %6.1f -> %6.1f" % (k * 6, lo / scale, hi / scale))
        seen += 1
        if limit and seen >= limit:
            break


print("== %s ==" % path)
print("image %dx%d scale %.4f" % (w, h, scale))
print("strip right edge: css %.1f" % (strip_edge / scale))
band(glyph_rows, "glyph ink inside the strip")
band(word_cols, "word ink in the label column", limit=12)
