"""Locate and characterise the partially-transparent original-ink pixels."""
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\scripts')
import generate_favicons as G

mark = G._load_mark()
orig = Image.open(G.LOGO).convert('RGB')
top, bottom, left, right = G.MARK_BOX
crop = orig.crop((left, top, right, bottom))
source = np.asarray(crop).astype(np.int16)
alpha = np.asarray(mark)[:, :, 3].astype(np.int16)

src_min = source.min(axis=2)
src_ink = (src_min < 200) | ((source.max(axis=2) - src_min) > 45)
lost = src_ink & (alpha < 100)

ys, xs = np.nonzero(lost)
print('count', len(ys))
print('source luminance of those pixels: min %d max %d mean %.0f' % (
    source[ys, xs].min(), source[ys, xs].max(), source[ys, xs].mean()))
print('their alpha: min %d max %d mean %.0f' % (alpha[ys, xs].min(), alpha[ys, xs].max(), alpha[ys, xs].mean()))

# How dark are they really? A pixel at luminance 190 is a faint fringe, not ink.
bands = [(0, 100), (100, 150), (150, 200), (200, 255)]
for lo, hi in bands:
    sel = (src_min[ys, xs] >= lo) & (src_min[ys, xs] < hi)
    print('  source min-channel %3d-%3d : %5d px' % (lo, hi, sel.sum()))

# Cluster them: are they thin fringes around strokes, or real blobs?
from scipy import ndimage
lab, n = ndimage.label(lost)
sizes = ndimage.sum(lost, lab, range(1, n + 1))
print('clusters:', n, ' largest', int(sizes.max()) if n else 0)
for i in np.argsort(-sizes)[:5]:
    if sizes[i] < 3:
        break
    lid = i + 1
    yy, xx = np.nonzero(lab == lid)
    print('   size %4d  bbox y %3d..%3d x %3d..%3d  max src min-channel %d' % (
        sizes[i], yy.min(), yy.max(), xx.min(), xx.max(), src_min[yy, xx].max()))
