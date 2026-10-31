from PIL import Image
import glob, os
for f in sorted(glob.glob(r'D:\SMART BUSINESSWRITER\.uitmp\fav_before\*.png')):
    im = Image.open(f).convert('RGBA')
    a = im.getchannel('A')
    bbox = a.getbbox()
    corners = [im.getpixel((0,0)), im.getpixel((im.width-1,0)), im.getpixel((0,im.height-1)), im.getpixel((im.width-1,im.height-1))]
    print(os.path.basename(f), im.size, 'alpha range', a.getextrema(), 'content bbox', bbox, 'corners', corners)
