"""Regenerate the favicon set inlined in `web/index.html` from `web/assets/logo.png`.

Run from `business_pipeline/`:

    $env:PYTHONPATH="src"; python scripts/generate_favicons.py

The owner's `logo.png` is RGB with no alpha channel and a solid `#FCFCFC` paper
background.  Inlining it as a favicon therefore shows a white card around the
mark.  This script rebuilds the mark with a real alpha channel: the paper
*outside* the artwork becomes transparent, while the paper *inside* the book
stays opaque so the book still reads as a solid object on a dark browser tab.

Only the book and the bars are kept - the `Smart BusinessWriter` wordmark is
part of the lockup, not part of the mark, and the favicon must not carry it.

The icons are written to `web/assets/favicon-*.png` for inspection and are
also inlined into `web/index.html` as data URIs, because the server serves
only `/` and `/api/*` (a `/assets/<path>` route is still an open request in
`web/DESIGN_NOTES.md`).

Requires Pillow and SciPy.
"""

import base64
import io
import os
import re
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
ASSETS = os.path.join(WEB, "assets")
LOGO = os.path.join(ASSETS, "logo.png")
PAGE = os.path.join(WEB, "index.html")

# The mark block in logo.png: the book and the four bars, above the wordmark.
# The mark's last ink row is 593 and the wordmark's first is 599, so the crop
# stops at 598: a couple of rows lower and the top of an "S" creeps in.
MARK_BOX = (126, 598, 356, 930)  # top, bottom, left, right

# The paper the owner's PNG was flattened onto.
PAPER = np.array([252.0, 252.0, 252.0])

# Closing radius used to seal the gaps between the book's page strokes so the
# paper between them is treated as interior rather than as background.
PAGE_CLOSE = 16

# Sizes inlined into the page head.
ICON_SIZES = (16, 32, 64)
APPLE_SIZE = 180

# Fraction of the tile the mark occupies.
FILL = 0.90


def _load_mark():
    """Return the book-and-bar mark from logo.png as an RGBA image."""
    image = Image.open(LOGO).convert("RGB")
    crop = np.asarray(image).astype(np.float64)
    top, bottom, left, right = MARK_BOX
    crop = crop[top:bottom, left:right]

    background = PAPER.reshape(1, 1, 3)

    # Confidently ink pixels: dark navy strokes, or the saturated green/teal
    # bars.  Everything else is paper, or an anti-aliased edge between the two.
    low = crop.min(axis=2)
    high = crop.max(axis=2)
    solid = (low < 120) | ((high - low) > 70)

    # Coverage of every pixel against the paper background, using the colour
    # of the nearest confident ink pixel as the ink underneath.
    _, (iy, ix) = ndimage.distance_transform_edt(~solid, return_indices=True)
    ink = crop[iy, ix]
    numerator = ((background - crop) * (background - ink)).sum(axis=2)
    denominator = ((background - ink) ** 2).sum(axis=2)
    coverage = np.clip(
        np.where(denominator > 1.0, numerator / np.maximum(denominator, 1e-6), 0.0),
        0.0,
        1.0,
    )
    coverage = np.where(solid, 1.0, coverage)

    # The bars are solid slabs; the book is drawn as strokes.  Closing the
    # book's own components seals the gaps between its page strokes, so the
    # paper between them reads as the interior of the book and stays opaque.
    labels, count = ndimage.label(solid)
    objects = ndimage.find_objects(labels)
    structure = ndimage.generate_binary_structure(2, 2)
    body = np.zeros_like(solid)
    for index, window in enumerate(objects):
        if window is None:
            continue
        height = window[0].stop - window[0].start
        width = window[1].stop - window[1].start
        component = labels == index + 1
        filled = component.sum() / float(height * width)
        # A bar is a dense, narrow slab; a book part is a set of thin strokes.
        if filled > 0.6 and width < 0.35 * crop.shape[1]:
            continue
        closed = ndimage.binary_closing(component, structure=structure, iterations=PAGE_CLOSE)
        body |= ndimage.binary_fill_holes(closed)
    interior = body & ~solid

    alpha = coverage.copy()
    alpha[interior] = 1.0
    alpha[solid] = 1.0

    # Undo the flattening against the paper so the edges keep their colour.
    safe = np.maximum(alpha, 1e-6)[:, :, None]
    rgb = np.where(
        (alpha < 0.999)[:, :, None],
        np.clip((crop - (1 - alpha[:, :, None]) * background) / safe, 0, 255),
        crop,
    )
    rgb[interior] = PAPER

    return Image.fromarray(np.dstack([rgb, alpha * 255]).astype(np.uint8), "RGBA")


def _render(mark, size):
    """Scale the mark into a square tile of `size` pixels, keeping its aspect."""
    bounds = mark.getchannel("A").getbbox()
    trimmed = mark.crop(bounds)
    width, height = trimmed.size
    scale = (size * FILL) / float(max(width, height))
    scaled = trimmed.resize(
        (max(1, int(round(width * scale))), max(1, int(round(height * scale)))),
        Image.LANCZOS,
    )
    tile = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    tile.alpha_composite(scaled, ((size - scaled.width) // 2, (size - scaled.height) // 2))
    return tile


def _encode(image):
    """Return the PNG bytes for an image."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _data_uri(payload):
    return "data:image/png;base64," + base64.b64encode(payload).decode("ascii")


def _patch_page(uris):
    """Replace the icon links in the page head with the freshly built ones."""
    with open(PAGE, encoding="utf-8", newline="") as stream:
        html = stream.read()

    links = [
        '<link rel="icon" type="image/png" sizes="16x16" href="%s">' % uris[16],
        '<link rel="icon" type="image/png" sizes="32x32" href="%s">' % uris[32],
        '<link rel="icon" type="image/png" sizes="64x64" href="%s">' % uris[64],
        '<link rel="apple-touch-icon" sizes="180x180" href="%s">' % uris[180],
    ]

    pattern = re.compile(
        r'<link rel="(?:icon|apple-touch-icon)"[^>]*?href="data:image/png;base64,[^"]*"[^>]*?>'
    )
    found = pattern.findall(html)
    if len(found) != len(links):
        raise SystemExit(
            "expected %d icon links in %s, found %d" % (len(links), PAGE, len(found))
        )
    index = [0]

    def swap(match):
        link = links[index[0]]
        index[0] += 1
        return link

    html = pattern.sub(swap, html)
    with open(PAGE, "w", encoding="utf-8", newline="") as stream:
        stream.write(html)
    return len(found)


def main():
    if not os.path.exists(LOGO):
        raise SystemExit("missing source logo: %s" % LOGO)

    mark = _load_mark()
    bounds = mark.getchannel("A").getbbox()
    print("mark extracted: %dx%d (transparent outside, opaque pages inside)" % (
        bounds[2] - bounds[0], bounds[3] - bounds[1]))

    uris = {}
    for size in list(ICON_SIZES) + [APPLE_SIZE]:
        tile = _render(mark, size)
        path = os.path.join(ASSETS, "favicon-%d.png" % size)
        tile.save(path)
        uris[size] = _data_uri(tile)
        print("wrote %s (%d bytes)" % (os.path.relpath(path, ROOT), os.path.getsize(path)))

    patched = _patch_page(uris)
    print("inlined %d icons into %s" % (patched, os.path.relpath(PAGE, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
