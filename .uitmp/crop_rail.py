"""Crop the left strip of a screenshot and upscale it for inspection.

Usage: python crop_rail.py <png> <out.png> [x0] [x1] [scale] [y0] [y1]
"""
import sys

from PIL import Image

src = sys.argv[1]
dst = sys.argv[2]
x0 = int(sys.argv[3]) if len(sys.argv) > 3 else 0
x1 = int(sys.argv[4]) if len(sys.argv) > 4 else 70
scale = int(sys.argv[5]) if len(sys.argv) > 5 else 6
y0 = int(sys.argv[6]) if len(sys.argv) > 6 else 0
y1 = int(sys.argv[7]) if len(sys.argv) > 7 else None

im = Image.open(src).convert("RGB")
w, h = im.size
y1 = h if y1 is None else min(y1, h)
crop = im.crop((x0, y0, x1, y1))
crop = crop.resize((crop.width * scale, crop.height * scale), Image.NEAREST)
crop.save(dst)
print("%s %dx%d -> %s %dx%d (css x %d..%d of %d)" % (src, w, h, dst, crop.width, crop.height, x0, x1, w))
