"""Prototype v3: region confirmed (mark.png is a downscale of logo.png[130:598, 358:926]).
Test closing radii so the book's paper interior stays opaque while the exterior paper goes."""
import numpy as np
from PIL import Image
from scipy import ndimage

LOGO = r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\assets\logo.png'
OUT = r'D:\SMART BUSINESSWRITER\.uitmp\_proto3'

im = Image.open(LOGO).convert('RGB')
crop = np.asarray(im).astype(np.float64)[130:598, 358:926]
print('crop', crop.shape)

paper = np.array([252.0, 252.0, 252.0])
bg = paper.reshape(1, 1, 3)

cmn = crop.min(axis=2)
cmx = crop.max(axis=2)
solid = (cmn < 120) | ((cmx - cmn) > 70)

# coverage against nearest solid colour
dist, (iy, ix) = ndimage.distance_transform_edt(~solid, return_indices=True)
fg = crop[iy, ix]
num = ((bg - crop) * (bg - fg)).sum(axis=2)
den = ((bg - fg) ** 2).sum(axis=2)
cov = np.clip(np.where(den > 1.0, num / np.maximum(den, 1e-6), 0.0), 0.0, 1.0)
cov = np.where(solid, 1.0, cov)

results = []
for R in (0, 4, 6, 8, 10, 12, 14):
    if R == 0:
        filled = solid
    else:
        st = ndimage.generate_binary_structure(2, 2)
        disk = ndimage.binary_dilation(solid, st, iterations=R)
        filled = ndimage.binary_fill_holes(disk)
    interior = filled & ~solid
    alpha = cov.copy()
    alpha[interior] = 1.0
    alpha[solid] = 1.0

    safe = np.maximum(alpha, 1e-6)[:, :, None]
    rgb = np.where((alpha < 0.999)[:, :, None],
                   np.clip((crop - (1 - alpha[:, :, None]) * bg) / safe, 0, 255),
                   crop)
    rgba = np.dstack([rgb, alpha * 255]).astype(np.uint8)
    out = Image.fromarray(rgba, 'RGBA')
    name = f'{OUT}_r{R}'
    out.save(name + '_mark.png')
    for bgname, col in (('dark', (24, 26, 30)), ('magenta', (255, 0, 255))):
        flat = Image.new('RGBA', out.size, col + (255,))
        flat.alpha_composite(out)
        flat.convert('RGB').resize((out.width * 2, out.height * 2), Image.LANCZOS).save(f'{name}__{bgname}.png')
    print('R=%2d interior=%.3f transparent=%.3f' % (R, interior.mean(), (alpha < 0.01).mean()))
