import numpy as np
from PIL import Image
im = Image.open(r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\assets\logo.png').convert('RGB')
a = np.asarray(im).astype(np.int16)
mn = a.min(axis=2); mx = a.max(axis=2)
ink = (mn < 200) | ((mx - mn) > 45)
print('ink pixel counts per row, y 585..615 (columns 356..930):')
for y in range(585, 616):
    row = ink[y, 356:930]
    xs = np.nonzero(row)[0]
    if len(xs):
        print('  y=%d  n=%3d  x=%d..%d' % (y, len(xs), xs.min()+356, xs.max()+356))
    else:
        print('  y=%d  n=  0' % y)
