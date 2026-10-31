"""Prototype v5: closing (dilate+erode) preserves the outer boundary -> no halo.
Find the radius that seals the book's page gaps without swelling the silhouette."""
import numpy as np
from PIL import Image
from scipy import ndimage

LOGO = r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\assets\logo.png'
OUT = r'D:\SMART BUSINESSWRITER\.uitmp\_proto5'

im = Image.open(LOGO).convert('RGB')
crop = np.asarray(im).astype(np.float64)[126:602, 356:930]
paper = np.array([252.0, 252.0, 252.0])
bg = paper.reshape(1, 1, 3)

cmn = crop.min(axis=2)
cmx = crop.max(axis=2)
solid = (cmn < 120) | ((cmx - cmn) > 70)

_, (iy, ix) = ndimage.distance_transform_edt(~solid, return_indices=True)
fg = crop[iy, ix]
num = ((bg - crop) * (bg - fg)).sum(axis=2)
den = ((bg - fg) ** 2).sum(axis=2)
cov = np.clip(np.where(den > 1.0, num / np.maximum(den, 1e-6), 0.0), 0.0, 1.0)
cov = np.where(solid, 1.0, cov)

disk = ndimage.generate_binary_structure(2, 2)

for R in (6, 10, 14, 18, 24):
    closed = ndimage.binary_closing(solid, structure=disk, iterations=R)
    body = ndimage.binary_fill_holes(closed)
    interior = body & ~solid
    alpha = cov.copy()
    alpha[interior] = 1.0
    alpha[solid] = 1.0
    safe = np.maximum(alpha, 1e-6)[:, :, None]
    rgb = np.where((alpha < 0.999)[:, :, None],
                   np.clip((crop - (1 - alpha[:, :, None]) * bg) / safe, 0, 255),
                   crop)
    out = Image.fromarray(np.dstack([rgb, alpha * 255]).astype(np.uint8), 'RGBA')
    out.save(f'{OUT}_r{R}_mark.png')
    flat = Image.new('RGBA', out.size, (255, 0, 255, 255))
    flat.alpha_composite(out)
    flat.convert('RGB').resize((out.width * 2, out.height * 2), Image.LANCZOS).save(f'{OUT}_r{R}__magenta.png')
    print('R=%2d closed=%.3f body=%.3f interior=%.3f transparent=%.3f'
          % (R, closed.mean(), body.mean(), interior.mean(), (alpha < 0.01).mean()))
