"""Prototype v4: label-based interior detection (no dilation halo)."""
import numpy as np
from PIL import Image
from scipy import ndimage

LOGO = r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\assets\logo.png'
OUT = r'D:\SMART BUSINESSWRITER\.uitmp\_proto4'

im = Image.open(LOGO).convert('RGB')
crop = np.asarray(im).astype(np.float64)[126:602, 356:930]
print('crop', crop.shape)

paper = np.array([252.0, 252.0, 252.0])
bg = paper.reshape(1, 1, 3)

cmn = crop.min(axis=2)
cmx = crop.max(axis=2)
solid = (cmn < 120) | ((cmx - cmn) > 70)

# --- coverage against nearest solid colour --------------------------------
_, (iy, ix) = ndimage.distance_transform_edt(~solid, return_indices=True)
fg = crop[iy, ix]
num = ((bg - crop) * (bg - fg)).sum(axis=2)
den = ((bg - fg) ** 2).sum(axis=2)
cov = np.clip(np.where(den > 1.0, num / np.maximum(den, 1e-6), 0.0), 0.0, 1.0)
cov = np.where(solid, 1.0, cov)

# --- label free (paper) regions; those touching the border are exterior ---
lab, n = ndimage.label(~solid)
border = set(lab[0].tolist()) | set(lab[-1].tolist()) | set(lab[:, 0].tolist()) | set(lab[:, -1].tolist())
border.discard(0)
exterior = np.isin(lab, list(border))
enclosed = ~exterior & ~solid
print('free regions:', n, ' exterior frac %.3f' % exterior.mean(),
      ' enclosed frac %.4f' % enclosed.mean())

sizes = ndimage.sum(~solid, lab, range(1, n + 1))
for i in np.argsort(-sizes)[:6]:
    lid = i + 1
    ys, xs = np.nonzero(lab == lid)
    print('  region %d size %d bbox y %d..%d x %d..%d exterior=%s'
          % (lid, sizes[i], ys.min(), ys.max(), xs.min(), xs.max(), lid in border))

alpha = cov.copy()
alpha[enclosed] = 1.0
alpha[solid] = 1.0

safe = np.maximum(alpha, 1e-6)[:, :, None]
rgb = np.where((alpha < 0.999)[:, :, None],
               np.clip((crop - (1 - alpha[:, :, None]) * bg) / safe, 0, 255),
               crop)

out = Image.fromarray(np.dstack([rgb, alpha * 255]).astype(np.uint8), 'RGBA')
out.save(OUT + '_mark.png')
Image.fromarray((enclosed * 255).astype(np.uint8)).save(OUT + '_enclosed.png')

for name, col in (('light', (255, 255, 255)), ('dark', (24, 26, 30)), ('magenta', (255, 0, 255))):
    flat = Image.new('RGBA', out.size, col + (255,))
    flat.alpha_composite(out)
    flat.convert('RGB').resize((out.width * 2, out.height * 2), Image.LANCZOS).save(f'{OUT}__{name}.png')
print('done')
