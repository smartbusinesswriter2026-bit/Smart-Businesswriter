"""Side-by-side: old favicon vs new favicon, on light and dark."""
from PIL import Image

OLD = r'D:\SMART BUSINESSWRITER\.uitmp\fav_before'
NEW = r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\assets'
OUT = r'D:\SMART BUSINESSWRITER\.uitmp\_sbs'

pairs = [(0, 16, '0_icon_16x16.png'), (1, 32, '1_icon_32x32.png'), (2, 64, '2_icon_64x64.png')]
ZOOM = 6

for idx, size, name in pairs:
    old = Image.open(rf'{OLD}\{name}').convert('RGBA')
    new = Image.open(rf'{NEW}\favicon-{size}.png').convert('RGBA')
    for theme, col in (('light', (255, 255, 255)), ('dark', (24, 26, 30))):
        row = Image.new('RGB', (size * 2 + 20, size), col)
        for k, im in enumerate((old, new)):
            flat = Image.new('RGBA', (size, size), col + (255,))
            flat.alpha_composite(im)
            row.paste(flat.convert('RGB'), (k * (size + 20), 0))
        row.resize((row.width * ZOOM, row.height * ZOOM), Image.NEAREST).save(
            rf'{OUT}_{size}_{theme}.png')
print('done')
