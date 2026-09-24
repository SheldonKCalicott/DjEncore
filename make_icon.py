from PIL import Image, ImageDraw

img = Image.new('RGBA', (256, 256), (16, 17, 24, 255))
draw = ImageDraw.Draw(img)
# main rounded square
for r in range(18, 0, -2):
    draw.rounded_rectangle((24, 24, 232, 232), radius=36, outline=(109, 124, 255, 255), width=16)
# accent slash
draw.polygon([(78, 180), (180, 78), (208, 106), (106, 208)], fill=(255, 255, 255, 255))
# center dot
for size in [18, 12]:
    draw.ellipse((119 - size//2, 119 - size//2, 119 + size//2, 119 + size//2), fill=(109, 124, 255, 255))
img.save('src/app.ico')
print('created src/app.ico')
