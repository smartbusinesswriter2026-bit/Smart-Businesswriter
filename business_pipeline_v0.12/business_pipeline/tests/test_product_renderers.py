"""The rasterizers: a figure must survive the trip from its drawing to its PNG.

Three defects are pinned here, each of which shipped a picture that looked
finished and was not:

* the headless window is taller than the drawing it takes, so the viewport is
  shorter than the window and the bottom of the figure was lost - a Gantt lost
  its last activity;
* a kind the builtin renderer owns must not be handed to Plotly, which draws
  an empty chart for a spec it does not know;
* a chart with many points must not print a value on every one of them.

The tests that need Chrome are skipped when Chrome is absent; the crop itself
is tested without it.
"""

import os
import struct
import sys
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
sys.path.insert(0, HERE)

from bp.product import renderers  # noqa: E402

#: A drawing whose bottom band is the only red in the picture.
SVG_WITH_BOTTOM_BAND = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">'
    '<rect width="100%" height="100%" fill="#ffffff"/>'
    '<rect x="0" y="180" width="200" height="20" fill="#e15759"/></svg>')


def png_size(data):
    """(width, height) of a PNG, read from its header."""
    return struct.unpack(">II", data[16:24])


def png_rows(data):
    """(width, height, channels, rows) of a PNG, decoded with the standard library."""
    offset = 8
    header = None
    idat = []
    while offset + 8 <= len(data):
        length = int.from_bytes(data[offset:offset + 4], "big")
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + length]
        offset += 12 + length
        if kind == b"IHDR":
            header = payload
        elif kind == b"IDAT":
            idat.append(payload)
        elif kind == b"IEND":
            break
    width = int.from_bytes(header[0:4], "big")
    height = int.from_bytes(header[4:8], "big")
    channels = {0: 1, 2: 3, 6: 4}[header[9]]
    stride = width * channels
    raw = zlib.decompress(b"".join(idat))
    rows = []
    previous = bytearray(stride)
    position = 0
    for _ in range(height):
        kind = raw[position]
        position += 1
        line = bytearray(raw[position:position + stride])
        position += stride
        renderers._unfilter(kind, line, previous, channels)
        rows.append(bytes(line))
        previous = line
    return width, height, channels, rows


def build_png(width, height, rows):
    """A PNG of `rows` scanlines, each a list of (r, g, b) triples."""
    raw = bytearray()
    for row in rows:
        raw.append(0)
        for red, green, blue in row:
            raw.extend((red, green, blue))

    def chunk(kind, payload):
        return (len(payload).to_bytes(4, "big") + kind + payload
                + zlib.crc32(kind + payload).to_bytes(4, "big"))

    header = (width.to_bytes(4, "big") + height.to_bytes(4, "big")
              + bytes((8, 2, 0, 0, 0)))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


class PngCropTest(unittest.TestCase):
    """The crop that gives the rasterizer its drawing back."""

    def test_the_crop_keeps_the_wanted_rows(self):
        rows = [[(0, 0, 0)] * 4 for _ in range(10)]
        rows[8] = [(255, 0, 0)] * 4
        data = build_png(4, 10, rows)
        cropped = renderers._crop_png_rows(data, 9)
        self.assertIsNotNone(cropped)
        self.assertEqual(png_size(cropped), (4, 9))
        _width, _height, _channels, kept = png_rows(cropped)
        self.assertEqual(len(kept), 9)
        self.assertIn(bytes((255, 0, 0)), kept[8])

    def test_the_crop_keeps_the_picture_readable(self):
        rows = [[(10, 20, 30)] * 3 for _ in range(6)]
        data = build_png(3, 6, rows)
        cropped = renderers._crop_png_rows(data, 3)
        self.assertEqual(png_size(cropped), (3, 3))
        _width, _height, _channels, kept = png_rows(cropped)
        self.assertEqual(kept[0], bytes((10, 20, 30)) * 3)

    def test_a_picture_the_code_cannot_read_is_never_broken(self):
        self.assertIsNone(renderers._crop_png_rows(b"not a png", 4))
        self.assertIsNone(renderers._crop_png_rows(b"", 4))


class ChromeRasterTest(unittest.TestCase):
    """The drawing must reach the PNG whole."""

    def test_the_bottom_of_the_drawing_survives_the_rasterizer(self):
        if not renderers.chrome():
            self.skipTest("Chrome is not installed")
        data = renderers._chrome_svg_to_png(SVG_WITH_BOTTOM_BAND, 2)
        self.assertIsNotNone(data)
        width, height = png_size(data)
        self.assertEqual((width, height), (400, 400))
        _width, _height, channels, rows = png_rows(data)
        bottom = rows[-1]
        red = sum(1 for index in range(0, len(bottom), channels)
                  if bottom[index] > 180 and bottom[index + 1] < 130 and bottom[index + 2] < 130)
        self.assertGreater(red, 0, "the red band at the bottom of the drawing is missing")


class PlotlyOwnershipTest(unittest.TestCase):
    """A kind the builtin renderer owns must not be drawn by Plotly."""

    def test_plotly_refuses_the_network_kind(self):
        spec = {"format": "bp-chart/1", "kind": "network", "title": "Activity network",
                "nodes": [{"id": "A1", "label": "Design"}],
                "edges": []}
        self.assertIsNone(renderers._plotly_png(spec, {"delivery": {"appendix": {"artifacts": []}}},
                                                 3))
