"""Verify the extracted mark rigorously."""
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
src_max = source.max(axis=2)
src_ink = (src_min < 200) | ((src_max - src_min) > 45)

print('=== 1. no original ink was dropped ===')
lost = src_ink & (alpha < 100)
print('original ink pixels now transparent: %d of %d' % (lost.sum(), src_ink.sum()))
if lost.any():
    ys, xs = np.nonzero(lost)
    print('   rows %d..%d cols %d..%d' % (ys.min(), ys.max(), xs.min(), xs.max()))

print()
print('=== 2. what became transparent must have been paper ===')
gone = alpha < 8
not_paper = gone & ~((src_min >= 235) & (src_max - src_min < 25))
print('transparent but visibly coloured: %d px (%.4f%% of transparent area)' % (
    not_paper.sum(), 100.0 * not_paper.sum() / max(gone.sum(), 1)))
if not_paper.any():
    ys, xs = np.nonzero(not_paper)
    print('   rows %d..%d cols %d..%d' % (ys.min(), ys.max(), xs.min(), xs.max()))

print()
print('=== 3. the book page interior stayed opaque ===')
opaque = alpha > 200
ink_core = (src_min < 120) | ((src_max - src_min) > 70)
paper_interior = opaque & ~ink_core
print('opaque non-ink pixels (the book pages): %d px (%.3f%% of the tile)' % (
    paper_interior.sum(), 100.0 * paper_interior.mean()))
print('ink core pixels: %d (%.3f%%)' % (ink_core.sum(), 100.0 * ink_core.mean()))
print('fully transparent: %d (%.3f%%)' % (gone.sum(), 100.0 * gone.mean()))

print()
print('=== 4. no stray islands (wordmark fragments) ===')
from scipy import ndimage
lab, n = ndimage.label(ink_core)
sizes = ndimage.sum(ink_core, lab, range(1, n + 1))
for i in np.argsort(-sizes)[:8]:
    lid = i + 1
    ys, xs = np.nonzero(lab == lid)
    print('   component size %7d  bbox y %3d..%3d x %3d..%3d' % (
        sizes[i], ys.min(), ys.max(), xs.min(), xs.max()))

print()
print('=== 5. rounded-reconstruction sanity ===')
paper_bg = Image.new('RGBA', crop.size, (252, 252, 252, 255))
paper_bg.alpha_composite(mark)
recomposed = np.asarray(paper_bg.convert('RGB')).astype(np.int16)
diff = np.abs(recomposed - source).max(axis=2)
print('mean %.2f  p95 %.0f  p99 %.0f  max %d' % (
    diff.mean(), np.percentile(diff, 95), np.percentile(diff, 99), diff.max()))
print('pixels off by >60: %d (%.4f%%)' % ((diff > 60).sum(), 100.0 * (diff > 60).mean()))
