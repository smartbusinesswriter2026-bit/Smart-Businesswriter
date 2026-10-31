import numpy as np
from PIL import Image
base = r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\assets'
for s in (16, 32, 64, 180):
    im = Image.open(rf'{base}\favicon-{s}.png').convert('RGBA')
    a = np.asarray(im)
    corners = [tuple(a[y, x]) for (x, y) in ((0,0),(s-1,0),(0,s-1),(s-1,s-1))]
    alpha = a[:, :, 3]
    print(f'{s}x{s}: size={im.size} alpha range=({alpha.min()},{alpha.max()}) corners={corners}')
    # dark + light contact sheet, nearest-neighbour zoom
    for name, col in (('dark',(24,26,30)), ('light',(255,255,255))):
        flat = Image.new('RGBA', (s, s), col + (255,))
        flat.alpha_composite(im)
        flat.convert('RGB').resize((s*8, s*8), Image.NEAREST).save(rf'D:\SMART BUSINESSWRITER\.uitmp\_chk_{s}_{name}.png')
