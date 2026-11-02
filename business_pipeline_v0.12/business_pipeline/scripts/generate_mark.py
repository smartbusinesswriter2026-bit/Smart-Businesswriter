"""Rebuild the in-page mark (`web/assets/mark.png`) with a real alpha channel.

Run from `business_pipeline/`:

    $env:PYTHONPATH="src"; python scripts/generate_mark.py

The owner's `logo.png` is RGB with no alpha channel: the mark was flattened
onto solid `#FCFCFC` paper.  Inlined in the page, that paper came with it, so
the logo on the Home hero sat on a white card instead of on the hero wash,
and the logo in the chat button sat on a white rectangle instead of on the
round plate the CSS already draws.

This script cuts the mark out of `web/assets/logo.png` the same way
`scripts/generate_favicons.py` cuts it for the tab icons: the paper *outside*
the artwork becomes transparent, while the paper *inside* the book stays
opaque, so the book still reads as a solid object.  The result is written to
`web/assets/mark.png` and inlined into `web/index.html` as a data URI, because
the server serves only `/` and `/api/*` (a `/assets/<path>` route is still an
open request in `web/DESIGN_NOTES.md`).

The file on disk is written from the same encoded bytes that go into the
page, so `web/assets/mark.png` and the inline data URI cannot drift apart.

Requires Pillow and SciPy (the same offline tools the favicon build uses).
"""

import base64
import io
import os
import re
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
ASSETS = os.path.join(WEB, "assets")
PAGE = os.path.join(WEB, "index.html")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_favicons import _load_mark  # noqa: E402  (the shared alpha cut)

# The mark's canvas: the same size the previous asset used, so the page
# layout does not move when the mark is rebuilt.
MARK_SIZE = (168, 139)

# Paper noise in the owner's PNG leaves a veil of a few near-transparent
# pixels over the whole crop.  Below this alpha it is noise, not an edge.
FLOOR = 4


def _clean(pixels):
    """Drop the noise veil, keeping every real anti-aliased edge."""
    data = np.asarray(pixels).astype(np.uint8).copy()
    data[data[:, :, 3] < FLOOR] = 0
    return Image.fromarray(data, "RGBA")


def _resize(mark, size):
    """Scale an RGBA mark with premultiplied alpha.

    Straight alpha would drag the transparent pixels' colour into the edges
    and leave a pale halo on a dark surface; premultiplying first and
    unpremultiplying after keeps the edge on the ink's own colour.
    """
    data = np.asarray(mark).astype(np.float64)
    alpha = data[:, :, 3] / 255.0
    premultiplied = Image.fromarray(
        (data[:, :, :3] * alpha[:, :, None]).astype(np.uint8), "RGB")
    coverage = Image.fromarray(data[:, :, 3].astype(np.float32), "F")

    scaled = premultiplied.resize(size, Image.LANCZOS)
    scaled_alpha = np.clip(np.asarray(coverage.resize(size, Image.LANCZOS)), 0, 255)

    out = np.asarray(scaled, dtype=np.float64)
    alpha = scaled_alpha[:, :, None] / 255.0
    visible = alpha > 1e-4
    out = np.where(visible, out / np.maximum(alpha, 1e-4), 0.0)
    out = np.clip(out, 0, 255)

    stacked = np.dstack([out, scaled_alpha[:, :, None]])
    return Image.fromarray(stacked.astype(np.uint8), "RGBA")


def _encode(image):
    """Return the PNG bytes for an image."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _data_uri(payload):
    return "data:image/png;base64," + base64.b64encode(payload).decode("ascii")


def _patch_page(old_uri, new_uri):
    """Replace every inlined copy of the old mark with the new one."""
    with open(PAGE, encoding="utf-8", newline="") as stream:
        html = stream.read()

    found = html.count(old_uri)
    if found == 0:
        raise SystemExit("the old inlined mark is not in %s" % PAGE)
    html = html.replace(old_uri, new_uri)

    with open(PAGE, "w", encoding="utf-8", newline="") as stream:
        stream.write(html)
    return found


def main():
    mark = _clean(_load_mark())
    small = _resize(mark, MARK_SIZE)
    payload = _encode(small)

    path = os.path.join(ASSETS, "mark.png")
    with open(path, "wb") as stream:
        stream.write(payload)

    uri = _data_uri(payload)

    # The old inlined copy is the one the page still carries: same bytes as the
    # previous `mark.png`, 168x139 and RGB.  It is found by its data URI.
    with open(PAGE, encoding="utf-8", newline="") as stream:
        html = stream.read()
    old_uris = set(re.findall(r"data:image/png;base64,[A-Za-z0-9+/=]+", html))
    previous = []
    for candidate in old_uris:
        raw = base64.b64decode(candidate.split(",", 1)[1])
        try:
            image = Image.open(io.BytesIO(raw))
        except Exception:
            continue
        if image.size == MARK_SIZE and image.mode == "RGB":
            previous.append(candidate)
    if len(previous) != 1:
        raise SystemExit(
            "expected exactly one inlined 168x139 RGB mark in the page, found %d"
            % len(previous)
        )

    replaced = _patch_page(previous[0], uri)

    alpha = np.asarray(small.getchannel("A"))
    print("wrote %s (%d bytes, %dx%d RGBA)" % (
        os.path.relpath(path, ROOT), len(payload), MARK_SIZE[0], MARK_SIZE[1]))
    print("transparent pixels: %d of %d (%.1f%%)" % (
        int((alpha == 0).sum()), alpha.size,
        100.0 * float((alpha == 0).sum()) / alpha.size))
    print("replaced %d inlined copies in %s" % (
        replaced, os.path.relpath(PAGE, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
