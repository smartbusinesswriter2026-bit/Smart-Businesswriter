import numpy as np
from PIL import Image
p = r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\assets\logo.png'
im = Image.open(p).convert('RGB')
a = np.asarray(im).astype(np.int16)
# mark-only region (wordmark starts ~y=605)
crop = a[125:600, 355:935]
Image.fromarray(crop.astype(np.uint8)).save(r'D:\SMART BUSINESSWRITER\.uitmp\_mark_raw.png')
# colour classification map
def cls(pix):
    r,g,b = pix
    if r>235 and g>235 and b>235: return '.'
    if b>r and r<90: return 'N'      # navy
    if g>r and g>120 and b<190 and r<120: return 'G'  # green/teal
    return '?'
H,W = crop.shape[:2]
step_y = max(1,H//46); step_x = max(1,W//110)
for y in range(0, H, step_y):
    row = ''
    for x in range(0, W, step_x):
        row += cls(crop[y,x])
    print(row)
