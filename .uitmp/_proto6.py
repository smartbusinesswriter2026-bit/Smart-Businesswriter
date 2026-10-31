"""Prototype v6: separate the book's closed contour from the bars, fill the pages."""
import numpy as np
from PIL import Image
from scipy import ndimage

LOGO = r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\assets\logo.png'
OUT = r'D:\SMART BUSINESSWRITER\.uitmp\_proto6'

im = Image.open(LOGO).convert('RGB')
crop = np.asarray(im).astype(np.float64)[126:602, 356:930]
paper = np.array([252.0, 252.0, 252.0])
bg = paper.reshape(1, 1, 3)

cmn = crop.min(axis=2)
cmx = crop.max(axis=2)
solid = (cmn < 120) | ((cmx - cmn) > 70)

lab, n = ndimage.label(solid)
sizes = ndimage.sum(solid, lab, range(1, n + 1))
order = np.argsort(-sizes)
print('components (size, bbox):')
for i in order[:8]:
    lid = i + 1
    ys, xs = np.nonzero(lab == lid)
    print('  id=%2d size=%7d bbox y %3d..%3d x %3d..%3d' % (lid, sizes[i], ys.min(), ys.max(), xs.min(), xs.max()))

book_id = int(order[0]) + 1
book = lab == book_id
print('book component px', book.sum())

for R in (0, 3, 6, 10):
    src = book if R == 0 else ndimage.binary_closing(book, structure=ndimage.generate_binary_structure(2, 2), iterations=R)
    body = ndimage.binary_fill_holes(src)
    interior = body & ~book
    print('  R=%2d -> body %.3f interior %.3f' % (R, body.mean(), interior.mean()))
    Image.fromarray((interior * 255).astype(np.uint8)).save(f'{OUT}_int_R{R}.png')

# full render using the R=0 book body
_, (iy, ix) = ndimage.distance_transform_edt(~solid, return_indices=True)
fg = crop[iy, ix]
num = ((bg - crop) * (bg - fg)).sum(axis=2)
den = ((bg - fg) ** 2).sum(axis=2)
cov = np.clip(np.where(den > 1.0, num / np.maximum(den, 1e-6), 0.0), 0.0, 1.0)
cov = np.where(solid, 1.0, cov)

body = ndimage.binary_fill_holes(book)
interior = body & ~solid

alpha = cov.copy()
alpha[interior] = 1.0
alpha[solid] = 1.0
rgb = crop.copy()
rgb[interior] = paper           # pages are paper white
safe = np.maximum(alpha, 1e-6)[:, :, None]
rgb = np.where((alpha < 0.999)[:, :, None],
               np.clip((crop - (1 - alpha[:, :, None]) * bg) / safe, 0, 255),
               rgb)
out = Image.fromarray(np.dstack([rgb, alpha * 255]).astype(np.uint8), 'RGBA')
out.save(OUT + '_mark.png')
for name, col in (('light', (255, 255, 255)), ('dark', (24, 26, 30)), ('magenta', (255, 0, 255))):
    flat = Image.new('RGBA', out.size, col + (255,))
    flat.alpha_composite(out)
    flat.convert('RGB').resize((out.width * 2, out.height * 2), Image.LANCZOS).save(f'{OUT}__{name}.png')
print('done')
