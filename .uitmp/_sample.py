import numpy as np
from PIL import Image
im = Image.open(r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\assets\logo.png').convert('RGB')
a = np.asarray(im)
# horizontal scan through the book body (y=480 is inside the left page area)
for y in (430, 470, 500, 530):
    print(f'--- row y={y} (x 380..700 step 6) ---')
    print('  ', ' '.join(f'{a[y,x,0]:3d},{a[y,x,1]:3d},{a[y,x,2]:3d}' for x in range(380, 700, 6)))
