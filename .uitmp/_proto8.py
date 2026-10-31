"""Prototype v8: diagnose the book's contour; render variant A at real favicon sizes."""
import numpy as np
from PIL import Image
from scipy import ndimage

LOGO = r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\assets\logo.png'
OUT = r'D:\SMART BUSINESSWRITER\.uitmp\_proto8'

im = Image.open(LOGO).convert('RGB')
crop = np.asarray(im).astype(np.float64)[126:602, 356:930]
paper = np.array([252.0, 252.0, 252.0])
bg = paper.reshape(1, 1, 3)

cmn = crop.min(axis=2)
cmx = crop.max(axis=2)
solid = (cmn < 120) | ((cmx - cmn) > 70)

lab, n = ndimage.label(solid)
sizes = ndimage.sum(solid, lab, range(1, n + 1))
book_id = int(np.argmax(sizes)) + 1
book = lab == book_id

# dump masks for diagnosis
Image.fromarray((book * 255).astype(np.uint8)).save(OUT + '_bookmask.png')
st = ndimage.generate_binary_structure(2, 2)
closed = ndimage.binary_closing(book, structure=st, iterations=14)
Image.fromarray((closed * 255).astype(np.uint8)).save(OUT + '_closed.png')
body = ndimage.binary_fill_holes(closed)
Image.fromarray((body * 255).astype(np.uint8)).save(OUT + '_body.png')
print('book px', book.sum(), 'closed px', closed.sum(), 'body px', body.sum())

# ---- variant A: paper fully transparent (faithful line-art book) ----------
_, (iy, ix) = ndimage.distance_transform_edt(~solid, return_indices=True)
fg = crop[iy, ix]
num = ((bg - crop) * (bg - fg)).sum(axis=2)
den = ((bg - fg) ** 2).sum(axis=2)
cov = np.clip(np.where(den > 1.0, num / np.maximum(den, 1e-6), 0.0), 0.0, 1.0)
cov = np.where(solid, 1.0, cov)

safe = np.maximum(cov, 1e-6)[:, :, None]
rgbA = np.where((cov < 0.999)[:, :, None],
                np.clip((crop - (1 - cov[:, :, None]) * bg) / safe, 0, 255),
                crop)
A = Image.fromarray(np.dstack([rgbA, cov * 255]).astype(np.uint8), 'RGBA')

# ---- variant B: book page interior kept opaque white ---------------------
alphaB = cov.copy()
alphaB[body & ~solid] = 1.0
rgbB = crop.copy()
rgbB[body & ~solid] = paper
safeB = np.maximum(alphaB, 1e-6)[:, :, None]
rgbB = np.where((alphaB < 0.999)[:, :, None],
                np.clip((crop - (1 - alphaB[:, :, None]) * bg) / safeB, 0, 255),
                rgbB)
B = Image.fromarray(np.dstack([rgbB, alphaB * 255]).astype(np.uint8), 'RGBA')


def bbox(im):
    return im.getchannel('A').getbbox()


for tag, img in (('A', A), ('B', B)):
    bb = bbox(img)
    print(tag, 'bbox', bb, 'size', (bb[2] - bb[0], bb[3] - bb[1]))
    trimmed = img.crop(bb)
    for s in (16, 32, 64, 180):
        # fit the mark into the square with a small margin
        w, h = trimmed.size
        scale = (s * 0.86) / max(w, h)
        nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
        r = trimmed.resize((nw, nh), Image.LANCZOS)
        canvas = Image.new('RGBA', (s, s), (0, 0, 0, 0))
        canvas.alpha_composite(r, ((s - nw) // 2, (s - nh) // 2))
        canvas.save(f'{OUT}_{tag}_{s}.png')
        for bn, col in (('dark', (24, 26, 30)), ('light', (255, 255, 255))):
            flat = Image.new('RGBA', (s, s), col + (255,))
            flat.alpha_composite(canvas)
            flat.convert('RGB').resize((s * 8, s * 8), Image.NEAREST).save(f'{OUT}_{tag}_{s}__{bn}.png')
print('done')
