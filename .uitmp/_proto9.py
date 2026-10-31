"""Prototype v9: per-component closing -> page interiors opaque white, bars untouched."""
import numpy as np
from PIL import Image
from scipy import ndimage

LOGO = r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\assets\logo.png'
OUT = r'D:\SMART BUSINESSWRITER\.uitmp\_proto9'

im = Image.open(LOGO).convert('RGB')
crop = np.asarray(im).astype(np.float64)[126:602, 356:930]
paper = np.array([252.0, 252.0, 252.0])
bg = paper.reshape(1, 1, 3)

cmn = crop.min(axis=2)
cmx = crop.max(axis=2)
solid = (cmn < 120) | ((cmx - cmn) > 70)

lab, n = ndimage.label(solid)
sizes = ndimage.sum(solid, lab, range(1, n + 1))
st = ndimage.generate_binary_structure(2, 2)

# bars are narrow vertical components; book parts are wide/flat.
objs = ndimage.find_objects(lab)
bar_ids, book_ids = [], []
for i, sl in enumerate(objs):
    if sl is None:
        continue
    h = sl[0].stop - sl[0].start
    w = sl[1].stop - sl[1].start
    lid = i + 1
    if h > 2 * w and w < 0.35 * crop.shape[1]:
        bar_ids.append(lid)
    else:
        book_ids.append(lid)
print('bar ids', bar_ids, 'book ids', book_ids)
for lid in book_ids:
    sl = objs[lid - 1]
    print('  book comp', lid, 'size', int(sizes[lid - 1]), 'bbox y', sl[0].start, sl[0].stop, 'x', sl[1].start, sl[1].stop)

for R in (10, 14, 18, 22):
    body = np.zeros_like(solid)
    for lid in book_ids:
        comp = lab == lid
        closed = ndimage.binary_closing(comp, structure=st, iterations=R)
        body |= ndimage.binary_fill_holes(closed)
    interior = body & ~solid

    # coverage
    _, (iy, ix) = ndimage.distance_transform_edt(~solid, return_indices=True)
    fg = crop[iy, ix]
    num = ((bg - crop) * (bg - fg)).sum(axis=2)
    den = ((bg - fg) ** 2).sum(axis=2)
    cov = np.clip(np.where(den > 1.0, num / np.maximum(den, 1e-6), 0.0), 0.0, 1.0)
    cov = np.where(solid, 1.0, cov)

    alpha = cov.copy()
    alpha[interior] = 1.0
    alpha[solid] = 1.0
    rgb = crop.copy()
    rgb[interior] = paper
    safe = np.maximum(alpha, 1e-6)[:, :, None]
    rgb = np.where((alpha < 0.999)[:, :, None],
                   np.clip((crop - (1 - alpha[:, :, None]) * bg) / safe, 0, 255),
                   rgb)
    out = Image.fromarray(np.dstack([rgb, alpha * 255]).astype(np.uint8), 'RGBA')
    out.save(f'{OUT}_r{R}_mark.png')
    for bn, col in (('magenta', (255, 0, 255)), ('dark', (24, 26, 30))):
        flat = Image.new('RGBA', out.size, col + (255,))
        flat.alpha_composite(out)
        flat.convert('RGB').resize((out.width * 2, out.height * 2), Image.LANCZOS).save(f'{OUT}_r{R}__{bn}.png')
    print('R=%2d interior=%.3f transparent=%.3f' % (R, interior.mean(), (alpha < 0.01).mean()))
