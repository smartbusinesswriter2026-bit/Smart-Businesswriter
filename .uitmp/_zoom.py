from PIL import Image
im = Image.open(r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\assets\logo.png').convert('RGB')
# top-middle of the book where the bars come down
im.crop((356, 330, 930, 470)).resize((574*2, 140*2), Image.LANCZOS).save(r'D:\SMART BUSINESSWRITER\.uitmp\_zoom_top.png')
# bottom cover
im.crop((356, 470, 930, 600)).resize((574*2, 130*2), Image.LANCZOS).save(r'D:\SMART BUSINESSWRITER\.uitmp\_zoom_bottom.png')
print('ok')
