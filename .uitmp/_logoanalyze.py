import numpy as np
from PIL import Image
p = r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\assets\logo.png'
im = Image.open(p).convert('RGB')
a = np.asarray(im).astype(np.int16)
print('size', im.size)
print('corners', a[0,0], a[0,-1], a[-1,0], a[-1,-1])
print('bg value histogram (top 10 most common):')
flat = a.reshape(-1,3)
vals, counts = np.unique(flat[:,0], return_counts=True)
order = np.argsort(-counts)[:10]
for i in order: print('  R=', vals[i], 'count', counts[i])
# find near-white mask and row/col profile
white = (a.min(axis=2) >= 248)
rows = white.mean(axis=1)
print('row profile of white fraction (every 40 rows):')
for y in range(0, a.shape[0], 40):
    print('  y=', y, round(float(rows[y]),3))
