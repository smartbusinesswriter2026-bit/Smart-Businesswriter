"""Report the ink extent of each glyph in the collapsed rail strip.

Usage: python ink_rail.py <png> [x_max_css]
Prints, for every horizontal band that holds ink, the CSS x-extent of the ink
inside the strip so a clipped glyph is obvious.
"""
import sys

from PIL import Image

path = sys.argv[1]
x_max = int(sys.argv[2]) if len(sys.argv) > 2 else 45

im = Image.open(path).convert("RGB")
w, h = im.size
px = im.load()

GREEN = (10, 70, 50)


def is_green(c):
    return abs(c[0] - GREEN[0]) < 34 and abs(c[1] - GREEN[1]) < 34 and abs(c[2] - GREEN[2]) < 34


rows = []
for y in range(h):
    cols = [x for x in range(min(x_max, w)) if not is_green(px[x, y])]
    if cols:
        rows.append((y, min(cols), max(cols), len(cols)))

# group contiguous rows into glyph bands
bands = []
cur = None
for y, lo, hi, n in rows:
    if cur and y == cur[1] + 1:
        cur = (cur[0], y, min(cur[2], lo), max(cur[3], hi), cur[4] + n)
    else:
        if cur:
            bands.append(cur)
        cur = (y, y, lo, hi, n)
if cur:
    bands.append(cur)

print("== %s (strip 0..%d css px) ==" % (path, x_max))
for y0, y1, lo, hi, n in bands:
    if hi - lo < 3:
        continue
    print("y %4d..%4d  ink x %3d -> %3d  (width %2d)  %s"
          % (y0, y1, lo, hi, hi - lo + 1,
             "CLIPPED at %d" % x_max if hi >= x_max - 1 else ""))
