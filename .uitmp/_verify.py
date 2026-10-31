"""Verify the extracted mark: composite over paper and compare with the original crop."""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\scripts')
import generate_favicons as G

mark = G._load_mark()
orig = Image.open(G.LOGO).convert('RGB')
top, bottom, left, right = G.MARK_BOX
crop = orig.crop((left, top, right, bottom))

paper = Image.new('RGBA', crop.size, (252, 252, 252, 255))
paper.alpha_composite(mark)
recomposed = np.asarray(paper.convert('RGB')).astype(np.int16)
source = np.asarray(crop).astype(np.int16)

diff = np.abs(recomposed - source).max(axis=2)
print('reconstruction vs original crop: mean %.2f  p99 %.0f  max %d' % (
    diff.mean(), np.percentile(diff, 99), diff.max()))
bad = (diff > 40)
print('pixels differing >40: %d (%.3f%%)' % (bad.sum(), 100.0 * bad.mean()))
if bad.any():
    ys, xs = np.nonzero(bad)
    print('  worst rows %d..%d  cols %d..%d (crop coords)' % (
        ys.min(), ys.max(), xs.min(), xs.max()))
    # show a map of where the differences are
    step_y = max(1, bad.shape[0] // 40)
    step_x = max(1, bad.shape[1] // 100)
    for y in range(0, bad.shape[0], step_y):
        print('  ' + ''.join('#' if bad[y, x] else '.' for x in range(0, bad.shape[1], step_x)))

# Where the mark claims transparency, the original must be plain paper.
alpha = np.asarray(mark)[:, :, 3]
gone = alpha < 8
is_paper = (source.min(axis=2) >= 240)
leak = gone & ~is_paper
print('transparent pixels that were NOT plain paper: %d (%.4f%%)' % (
    leak.sum(), 100.0 * leak.mean() / max(gone.mean(), 1e-9)))
ys, xs = np.nonzero(leak)
if leak.any():
    print('  leak rows %d..%d cols %d..%d' % (ys.min(), ys.max(), xs.min(), xs.max()))

# Stray fragments: connected transparent-hole components fully enclosed by ink
from scipy import ndimage
ink = alpha > 200
print('ink fraction %.3f  opaque-paper fraction %.3f  transparent fraction %.3f' % (
    ink.mean(), ((alpha > 200) & ~ink).mean(), gone.mean()))
