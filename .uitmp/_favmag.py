from PIL import Image
for name in ['0_icon_16x16','1_icon_32x32','2_icon_64x64']:
    im = Image.open(rf'D:\SMART BUSINESSWRITER\.uitmp\fav_before\{name}.png').convert('RGBA')
    bg = Image.new('RGBA', im.size, (255,0,255,255))
    bg.alpha_composite(im)
    bg.convert('RGB').resize((im.width*10, im.height*10), Image.NEAREST).save(rf'D:\SMART BUSINESSWRITER\.uitmp\fav_before\{name}_mag.png')
print('ok')
