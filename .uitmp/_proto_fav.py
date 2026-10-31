"""Prototype: extract a true-alpha book+bar mark from web/assets/logo.png."""
import numpy as np
from PIL import Image
from scipy import ndimage

LOGO = r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\assets\logo.png'
OUT = r'D:\SMART BUSINESSWRITER\.uitmp\_proto'

im = Image.open(LOGO).convert('RGB')
a = np.asarray(im).astype(np.float64)

# ---- 1. locate the mark block (book + bars), above the wordmark -------------
ink = (a.min(axis=2) < 200) | ((a.max(axis=2) - a.min(axis=2)) > 45)
band = ink[:, 330:960]
rows = band.sum(axis=1)
gaps = [y for y in range(120, 800) if rows[y] == 0]
print('first empty row in band:', gaps[0] if gaps else None)

TOP = 125
BOT = 598
crop = a[TOP:BOT, 350:940]
print('crop', crop.shape)

# ---- 2. background estimate (paper) ---------------------------------------
paper = np.median(np.concatenate([
    crop[:8].reshape(-1, 3), crop[-8:].reshape(-1, 3),
    crop[:, :8].reshape(-1, 3), crop[:, -8:].reshape(-1, 3)]), axis=0)
print('paper estimate', paper)

# ---- 3. confident ink mask -----------------------------------------------
mn = crop.min(axis=2)
mx = crop.max(axis=2)
solid = (mn < 120) | ((mx - mn) > 70)

# ---- 4. nearest solid colour for every pixel ------------------------------
dist, (iy, ix) = ndimage.distance_transform_edt(~solid, return_indices=True)
fg = crop[iy, ix]

# ---- 5. least-squares coverage against paper ------------------------------
bg = paper.reshape(1, 1, 3)
num = ((bg - crop) * (bg - fg)).sum(axis=2)
den = ((bg - fg) ** 2).sum(axis=2)
cov = np.where(den > 1.0, num / np.maximum(den, 1e-6), 0.0)
cov = np.clip(cov, 0.0, 1.0)
cov = np.where(solid, 1.0, cov)

# ---- 6. outside = paper connected to the crop border -----------------------
free = ~solid
lab, n = ndimage.label(free)
border = set(lab[0].tolist()) | set(lab[-1].tolist()) | set(lab[:, 0].tolist()) | set(lab[:, -1].tolist())
border.discard(0)
outside = np.isin(lab, list(border))

alpha = np.where(outside, cov, 1.0)          # inside white pages stay opaque
alpha = np.where(solid, 1.0, alpha)

# unmix the outside pixels back to pure ink colour
safe = np.maximum(alpha, 1e-6)[:, :, None]
rgb = np.where((alpha < 1.0)[:, :, None],
               np.clip((crop - (1 - alpha[:, :, None]) * bg) / safe, 0, 255),
               crop)

rgba = np.dstack([rgb, alpha * 255]).astype(np.uint8)
out = Image.fromarray(rgba, 'RGBA')
out.save(OUT + '_mark.png')
print('alpha range', alpha.min(), alpha.max(), 'outside frac', outside.mean())

# ---- preview over light / dark --------------------------------------------
for name, col in (('light', (255, 255, 255)), ('dark', (24, 26, 30)), ('magenta', (255, 0, 255))):
    flat = Image.new('RGBA', out.size, col + (255,))
    flat.alpha_composite(out)
    flat.convert('RGB').resize((out.width * 2, out.height * 2), Image.LANCZOS).save(f'{OUT}__{name}.png')
print('done')
