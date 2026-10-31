from PIL import Image
im = Image.open(r'D:\SMART BUSINESSWRITER\.uitmp\fav_before\1_icon_32x32.png').convert('RGBA')
px = im.load()
for y in range(0, 32, 2):
    row = []
    for x in range(0, 32):
        r,g,b,a = px[x,y]
        if a == 0: row.append(' . ')
        elif r>235 and g>235 and b>235: row.append(' W ')   # opaque-ish white
        elif r>200 and g>200 and b>200: row.append(' w ')
        else: row.append(' # ')
    print(y, ''.join(row))
