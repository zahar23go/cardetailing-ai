from PIL import Image, ImageDraw, ImageFilter
import os

base = r"C:\Users\ZAHAR\cardetailing-ai\frontend\public\images"
src = Image.open(os.path.join(base, "login-car.jpg")).convert("RGB")
# Skip phone chrome spike (~130-150) + black gap; start at content ~200
# Skip header/face band at top
clean = src.crop((205, 115, 1545, 755))
ow, oh = clean.size
p = clean.load()
for y in range(oh):
    for x in range(min(14, ow)):
        r, g, b = p[x, y]
        f = (x / 14) ** 0.8
        p[x, y] = (int(r * f), int(g * f), int(b * f))
    for x in range(max(0, ow - 14), ow):
        r, g, b = p[x, y]
        f = ((ow - 1 - x) / 14) ** 0.8
        p[x, y] = (int(r * f), int(g * f), int(b * f))
for y in range(min(10, oh)):
    f = (y / 10) ** 0.7
    for x in range(ow):
        r, g, b = p[x, y]
        p[x, y] = (int(r * f), int(g * f), int(b * f))

clean.save(os.path.join(base, "login-car.png"), optimize=True)
clean.save(os.path.join(base, "bmw-x5-hero.jpg"), quality=93, optimize=True)
print("hero", clean.size)

# Verify left/top-right
clean.crop((0, 0, 40, oh)).save(os.path.join(base, "_v-left.png"))
clean.crop((ow - 80, 0, ow, 100)).save(os.path.join(base, "_v-tr.png"))

# Crisp gold sports-car outline SVG-like via high-res draw, then downscale
W, H = 420, 180
logo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(logo)
# sleek sports silhouette
pts = [
    (20, 110), (35, 95), (55, 88), (70, 70), (85, 55), (100, 48),
    (140, 42), (220, 42), (260, 48), (290, 62), (320, 78), (355, 88),
    (385, 95), (400, 108), (405, 122), (390, 128), (370, 118), (350, 128),
    (330, 118), (160, 118), (140, 128), (120, 118), (95, 128), (75, 118),
    (50, 128), (30, 120),
]
d.polygon(pts, fill=(212, 168, 75, 255))
# windshield
d.polygon([(105, 55), (145, 50), (155, 78), (100, 82)], fill=(15, 15, 15, 230))
d.polygon([(150, 50), (230, 48), (245, 75), (158, 78)], fill=(18, 18, 18, 210))
# wheels
for cx in (105, 340):
    d.ellipse([cx - 28, 105, cx + 28, 161], fill=(8, 8, 8, 255), outline=(232, 200, 106, 255), width=5)
    d.ellipse([cx - 10, 123, cx + 10, 143], fill=(232, 200, 106, 255))
# accent line
d.line([(80, 95), (350, 95)], fill=(166, 124, 45, 180), width=3)
logo = logo.resize((140, 60), Image.Resampling.LANCZOS)
logo.save(os.path.join(base, "header-car-logo.png"))
print("logo ok")
