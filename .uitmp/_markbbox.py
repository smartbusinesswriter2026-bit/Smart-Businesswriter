import numpy as np
from PIL import Image
p = r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\assets\logo.png'
im = Image.open(p).convert('RGB')
a = np.asarray(im).astype(np.int16)
H, W = a.shape[:2]
# artwork = pixels notably darker or more saturated than the near-white background
mx = a.max(axis=2); mn = a.min(axis=2)
art = (mx - mn) > 28          # saturated (navy/green/teal)
dark = mn < 215               # dark ink
mask = art | dark
# restrict to the upper region: the wordmark lockup sits lower down
top = mask[:600]
ys, xs = np.nonzero(top)
print('mark bbox in logo.png: x', xs.min(), xs.max(), ' y', ys.min(), ys.max())
# where does the wordmark start?
rows = mask.sum(axis=1)
for y in range(560, 720, 10):
    print(' y', y, 'ink px', rows[y])
