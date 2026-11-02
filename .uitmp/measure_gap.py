"""Measure the visible gaps in the Home hero.

The question is a visual one: how much white space sits between the logo and
"Smart Business Writer", and how much sits between that wordmark and
"Your reliable business writing assistant".  Element boxes do not answer it -
a line box carries half-leading above and below the glyphs - so this reads the
rendered pixels instead.
"""

import sys

from PIL import Image

path = sys.argv[1] if len(sys.argv) > 1 else r"D:\SMART BUSINESSWRITER\.uitmp\home_bigger.png"
image = Image.open(path).convert("L")
width, height = image.size
pixels = image.load()

INK = 170  # the artwork and the type are far darker than the paper


def row_ink(y, x0=120, x1=None):
    if x1 is None:
        x1 = width - 20
    count = 0
    for x in range(x0, x1):
        if pixels[x, y] < INK:
            count += 1
    return count


bands = []
current = None
for y in range(50, height):
    if row_ink(y) > 2:
        if current is None:
            current = [y, y]
        else:
            current[1] = y
    elif current is not None:
        bands.append(tuple(current))
        current = None
if current is not None:
    bands.append(tuple(current))

print("%s (%dx%d)" % (path, width, height))
for index, (top, bottom) in enumerate(bands):
    print("band %d: rows %d-%d (height %d)" % (index, top, bottom, bottom - top + 1))

if len(bands) >= 3:
    logo = bands[0]
    title = bands[1]
    slogan = bands[2]
    gap_above = title[0] - logo[1] - 1
    gap_below = slogan[0] - title[1] - 1
    print("")
    print("gap above the wordmark (logo ink -> wordmark cap): %d px" % gap_above)
    print("gap below the wordmark (wordmark base -> slogan cap): %d px" % gap_below)
    print("difference to close: %+d px" % (gap_below - gap_above))
