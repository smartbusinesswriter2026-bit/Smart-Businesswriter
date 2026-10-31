"""Prototype v2: keep the book's white page interiors opaque, drop only the exterior paper."""
import numpy as np
from PIL import Image
from scipy import ndimage

LOGO = r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\assets\logo.png'
OUT = r'D:\SMART BUSINESSWRITER\.uitmp\_proto2'

im = Image.open(LOGO).convert('RGB')
a = np.asarray(im).astype(np.float64)

mn = a.min(axis=2)
mx = a.max(axis=2)
ink = (mn < 200) | ((mx - mn) > 45)

# mark component = book + bars; take the largest blob in the upper band
band = ink[:620]
lab, n = ndimage.label(band)
sizes = ndimage.sum(band, lab, range(1, n + 1))
big = int(np.argmax(sizes)) + 1
ys, xs = np.nonzero(lab == big)
print('largest component bbox: x %d..%d  y %d..%d  px=%d' % (xs.min(), xs.max(), ys.min(), ys.max(), sizes.max()))

# second-largest blobs are the wordmark letters; confirm they sit below
others = [i + 1 for i in range(n) if i + 1 != big and sizes[i] > 200]
if others:
    oy = ndimage.center_of_mass(band, lab, others)
    print('other large blobs min/max center y:', round(min(c[0] for c in oy), 1), round(max(c[0] for c in oy), 1))

PAD = 6
TOP, BOT = ys.min() - PAD, ys.max() + PAD
LEFT, RIGHT = xs.min() - PAD, xs.max() + PAD
crop = a[TOP:BOT, LEFT:RIGHT]
print('crop', crop.shape)

paper = np.array([252.0, 252.0, 252.0])
bg = paper.reshape(1, 1, 3)

# --- solid ink -------------------------------------------------------------
cmn = crop.min(axis=2)
cmx = crop.max(axis=2)
solid = (cmn < 120) | ((cmx - cmn) > 70)

# --- coverage of every pixel against its nearest solid colour --------------
dist, (iy, ix) = ndimage.distance_transform_edt(~solid, return_indices=True)
fg = crop[iy, ix]
num = ((bg - crop) * (bg - fg)).sum(axis=2)
den = ((bg - fg) ** 2).sum(axis=2)
cov = np.clip(np.where(den > 1.0, num / np.maximum(den, 1e-6), 0.0), 0.0, 1.0)
cov = np.where(solid, 1.0, cov)

# --- which paper is *enclosed* by the artwork?  those stay opaque ---------
filled = ndimage.binary_fill_holes(solid)
enclosed = filled & ~solid

alpha = cov.copy()
alpha[enclosed] = 1.0
alpha[solid] = 1.0

# unmix partially covered pixels back to pure ink
safe = np.maximum(alpha, 1e-6)[:, :, None]
rgb = np.where((alpha < 0.999)[:, :, None],
               np.clip((crop - (1 - alpha[:, :, None]) * bg) / safe, 0, 255),
               crop)

rgba = np.dstack([rgb, alpha * 255]).astype(np.uint8)
out = Image.fromarray(rgba, 'RGBA')
out.save(OUT + '_mark.png')
print('enclosed paper frac: %.3f  transparent frac: %.3f' % (enclosed.mean(), (alpha < 0.01).mean()))

for name, col in (('light', (255, 255, 255)), ('dark', (24, 26, 30)), ('magenta', (255, 0, 255))):
    flat = Image.new('RGBA', out.size, col + (255,))
    flat.alpha_composite(out)
    flat.convert('RGB').resize((out.width * 2, out.height * 2), Image.LANCZOS).save(f'{OUT}__{name}.png')

# also dump the enclosed-paper mask so I can see what it decided
Image.fromarray((enclosed * 255).astype(np.uint8)).save(OUT + '_enclosed.png')
print('done')
