"""The workbench's brand assets must survive the trip into the page.

Two defects hide behind this file's name:

* a duplicated scaffold document at the top of `web/index.html` pushed the
  four icon links out of the document head, so the browser registered no
  favicon and fell back to `/favicon.ico` (a 404);
* the owner's PNG has no alpha channel, so the logo arrived on the page with
  the `#FCFCFC` paper around it and sat on a white card instead of on the
  hero wash.

The checks read the page and the PNG bytes with the standard library only -
the runtime never imports an imaging package, and neither does this test.
"""

import base64
import pathlib
import re
import unittest
import zlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "web" / "index.html"
ASSETS = ROOT / "web" / "assets"

DATA_URI = re.compile(r"data:image/png;base64,([A-Za-z0-9+/=]+)")


def _chunks(payload):
    """Yield the (kind, data) pairs of a PNG file."""
    offset = 8
    while offset + 8 <= len(payload):
        length = int.from_bytes(payload[offset:offset + 4], "big")
        kind = payload[offset + 4:offset + 8]
        yield kind, payload[offset + 8:offset + 8 + length]
        offset += 12 + length


def _paeth(left, up, upleft):
    estimate = left + up - upleft
    a, b, c = abs(estimate - left), abs(estimate - up), abs(estimate - upleft)
    if a <= b and a <= c:
        return left
    if b <= c:
        return up
    return upleft


def _rows(payload):
    """Return (width, height, rows) for an 8-bit RGBA PNG."""
    width = height = None
    compressed = b""
    for kind, data in _chunks(payload):
        if kind == b"IHDR":
            width = int.from_bytes(data[0:4], "big")
            height = int.from_bytes(data[4:8], "big")
            if data[8] != 8 or data[9] != 6:
                raise AssertionError("the image is not 8-bit RGBA")
        elif kind == b"IDAT":
            compressed += data
        elif kind == b"IEND":
            break
    if width is None:
        raise AssertionError("the file carries no IHDR")

    raw = zlib.decompress(compressed)
    stride = width * 4
    rows = []
    previous = bytearray(stride)
    offset = 0
    for _ in range(height):
        filter_type = raw[offset]
        offset += 1
        line = bytearray(raw[offset:offset + stride])
        offset += stride
        for index in range(stride):
            left = line[index - 4] if index >= 4 else 0
            up = previous[index]
            upleft = previous[index - 4] if index >= 4 else 0
            if filter_type == 0:
                pass
            elif filter_type == 1:
                line[index] = (line[index] + left) & 0xFF
            elif filter_type == 2:
                line[index] = (line[index] + up) & 0xFF
            elif filter_type == 3:
                line[index] = (line[index] + ((left + up) // 2)) & 0xFF
            elif filter_type == 4:
                line[index] = (line[index] + _paeth(left, up, upleft)) & 0xFF
            else:
                raise AssertionError("unknown PNG filter %d" % filter_type)
        rows.append(bytes(line))
        previous = line
    return width, height, rows


def _decode(uri):
    """Return the PNG bytes behind a data URI."""
    return base64.b64decode(uri.split(",", 1)[1])


class BrandAssetsTest(unittest.TestCase):
    def setUp(self):
        self.page = PAGE.read_text(encoding="utf-8")

    def _logo_uri(self):
        match = re.search(r'const MARK = "data:image/png;base64,[A-Za-z0-9+/=]+"', self.page)
        self.assertIsNotNone(match, "the page carries no inline mark")
        return match.group(0).split('"')[1]

    def test_the_page_is_one_document(self):
        # A second document at the top of the file puts the real <head> in the
        # body, where a browser will not read a favicon from it.
        self.assertEqual(self.page.count("<!doctype html>"), 1)
        self.assertEqual(self.page.count("<head>"), 1)
        self.assertNotIn("Content goes here", self.page)

    def test_the_icon_links_sit_in_the_document_head(self):
        head = self.page[self.page.index("<head>"):self.page.index("</head>")]
        self.assertEqual(head.count('rel="icon"'), 3)
        self.assertEqual(head.count('rel="apple-touch-icon"'), 1)

    def test_the_inline_logo_carries_no_paper(self):
        width, height, rows = _rows(_decode(self._logo_uri()))
        self.assertEqual(rows[0][3], 0, "the logo's corner is not transparent")
        opaque = sum(1 for row in rows for index in range(3, len(row), 4)
                     if row[index] == 255)
        self.assertGreater(opaque / float(width * height), 0.2,
                           "the artwork went missing with the paper")

    def test_the_mark_asset_is_the_inlined_logo(self):
        # The file on disk and the bytes in the page are the same image, so
        # the two cannot drift apart.
        self.assertEqual(_decode(self._logo_uri()),
                         (ASSETS / "mark.png").read_bytes())

    def test_the_favicons_carry_no_white_card(self):
        for size in (16, 32, 64, 180):
            with self.subTest(size=size):
                payload = (ASSETS / ("favicon-%d.png" % size)).read_bytes()
                _, _, rows = _rows(payload)
                self.assertEqual(rows[0][3], 0,
                                 "favicon-%d.png has an opaque corner" % size)


if __name__ == "__main__":
    unittest.main()
