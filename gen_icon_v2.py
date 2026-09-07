from PIL import Image, ImageDraw, ImageFont
W=1024
img=Image.new('RGBA',(W,W),(0,0,0,0))
d=ImageDraw.Draw(img)
d.rounded_rectangle([6,6,W-6,W-6], radius=176, fill=(13,18,30,255), outline=(78,90,122,255), width=12)
d.rounded_rectangle([22,22,W-22,W-22], radius=160, fill=None, outline=(255,255,255,22), width=8)
d.rounded_rectangle([34,34,W-34,W-34], radius=144, fill=(18,26,44,255))
housing=[W//2-196, 88, W//2+196, 728]
d.rounded_rectangle(housing, radius=88, fill=(20,20,24,255), outline=(92,98,112,255), width=9)
d.rounded_rectangle([housing[0]+8,housing[1]+8,housing[2]-8,housing[3]-8], radius=80, fill=(30,30,36,255), outline=(255,255,255,16), width=5)
cx=W//2
cys=[224,408,592]
cols=[(228,32,32),(242,192,18),(30,190,82)]
glows=[(255,70,70),(255,228,100),(80,255,140)]
for cy,col,glow in zip(cys, cols, glows):
    r=102
    d.ellipse([cx-r-22,cy-r-22,cx+r+22,cy+r+22], fill=glow+(30,))
    d.ellipse([cx-r-12,cy-r-12,cx+r+12,cy+r+12], fill=glow+(52,))
    d.ellipse([cx-r,cy-r,cx+r,cy+r], fill=col+(255,), outline=(255,255,255,255), width=9)
    d.ellipse([cx-52,cy-48,cx-6,cy-10], fill=(255,255,255,165))
    d.ellipse([cx-34,cy-32,cx-14,cy-14], fill=(255,255,255,255))
for y in [316,500]:
    d.rounded_rectangle([housing[0]+28,y-5,housing[2]-28,y+5], radius=5, fill=(14,14,18,255))
    d.rounded_rectangle([housing[0]+28,y-1,housing[2]-28,y+1], radius=2, fill=(255,255,255,18))
badge=[W//2-286, 774, W//2+286, 950]
d.rounded_rectangle(badge, radius=48, fill=(255,255,255,255), outline=(78,90,122,255), width=7)
try:
    f=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 142)
    s=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 34)
except:
    f=ImageFont.load_default(); s=f
d.text((W//2, 852), 'B30', fill=(14,18,30,255), font=f, anchor='mm')
d.text((W//2, 910), 'CONTROLLER', fill=(86,98,122,255), font=s, anchor='mm')
img.save(r'D:\Projects\B30.ico', sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(24,24),(16,16)])
img.resize((512,512), Image.LANCZOS).save(r'D:\Projects\B30_preview.png','PNG')
print('v2 saved')
