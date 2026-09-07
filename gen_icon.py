from PIL import Image, ImageDraw, ImageFont

W = 1024
img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# outer dark rounded square
d.rounded_rectangle([8, 8, W-8, W-8], radius=168, fill=(16, 22, 34, 255), outline=(70, 82, 110, 255), width=14)
d.rounded_rectangle([18, 18, W-18, W-18], radius=154, fill=None, outline=(255, 255, 255, 28), width=10)
d.rounded_rectangle([36, 36, W-36, W-36], radius=136, fill=(22, 30, 48, 255))

# traffic housing
housing = [W//2 - 210, 110, W//2 + 210, 760]
d.rounded_rectangle(housing, radius=96, fill=(18, 18, 22, 255), outline=(90, 96, 110, 255), width=10)
d.rounded_rectangle([housing[0]+10, housing[1]+10, housing[2]-10, housing[3]-10], radius=86, fill=(28, 28, 34, 255), outline=(255, 255, 255, 18), width=6)

cx = W // 2
centers_y = [260, 440, 620]
colors = [(232, 38, 38), (244, 196, 24), (34, 197, 94)]
glows = [(255, 90, 90), (255, 232, 120), (90, 255, 140)]

for cy, col, glow in zip(centers_y, colors, glows):
    r = 116
    d.ellipse([cx-r-18, cy-r-18, cx+r+18, cy+r+18], fill=glow + (38,))
    d.ellipse([cx-r-10, cy-r-10, cx+r+10, cy+r+10], fill=glow + (62,))
    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=col + (255,), outline=(255, 255, 255, 255), width=10)
    # highlight
    d.ellipse([cx-62, cy-56, cx-8, cy-10], fill=(255, 255, 255, 170))
    d.ellipse([cx-42, cy-38, cx-18, cy-16], fill=(255, 255, 255, 255))

for y in [350, 530]:
    d.rounded_rectangle([housing[0]+22, y-4, housing[2]-22, y+4], radius=4, fill=(12, 12, 16, 255))

# B30 badge
badge = [W//2 - 300, 790, W//2 + 300, 940]
d.rounded_rectangle(badge, radius=52, fill=(255, 255, 255, 255), outline=(70, 82, 110, 255), width=8)

try:
    font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 132)
    small = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 36)
except:
    font = ImageFont.load_default()
    small = font

d.text((W//2, 856), "B30", fill=(16, 22, 34, 255), font=font, anchor="mm")
d.text((W//2, 910), "CONTROLLER", fill=(70, 82, 110, 255), font=small, anchor="mm")

sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)]
img.save(r"D:\Projects\B30.ico", sizes=sizes)
print("B30.ico saved", sizes)

preview = img.resize((512, 512), Image.LANCZOS)
preview.save(r"D:\Projects\B30_preview.png", "PNG")
print("B30_preview.png saved", preview.size)
