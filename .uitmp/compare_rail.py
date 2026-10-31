"""Compose the before/after comparison of the collapsed rail."""
from PIL import Image, ImageDraw

BEFORE = r"D:\SMART BUSINESSWRITER\.uitmp\rail_scrollbar.png"
AFTER = r"D:\SMART BUSINESSWRITER\.uitmp\final_wide.png"
OUT = r"D:\SMART BUSINESSWRITER\.uitmp\rail_before_after.png"

X0, X1, Y0, Y1 = 0, 62, 170, 420   # the subject rows, in CSS px
SCALE = 3


def strip(path):
    im = Image.open(path).convert("RGB").crop((X0, Y0, X1, Y1))
    return im.resize((im.width * SCALE, im.height * SCALE), Image.LANCZOS)


a, b = strip(BEFORE), strip(AFTER)
gap = 24
canvas = Image.new("RGB", (a.width + b.width + gap, a.height + 70), (252, 252, 252))
canvas.paste(a, (0, 70))
canvas.paste(b, (a.width + gap, 70))
draw = ImageDraw.Draw(canvas)
draw.text((4, 8), "BEFORE - 45 px rail", fill=(163, 44, 44))
draw.text((4, 26), "the scrollbar lands on the icon", fill=(163, 44, 44))
draw.text((4, 44), "column; every glyph is cut", fill=(163, 44, 44))
draw.text((a.width + gap + 4, 8), "AFTER - 61 px rail", fill=(2, 120, 80))
draw.text((a.width + gap + 4, 26), "the scrollbar has its own", fill=(2, 120, 80))
draw.text((a.width + gap + 4, 44), "column; the glyphs are whole", fill=(2, 120, 80))
canvas.save(OUT)
print("saved", OUT, canvas.size)
