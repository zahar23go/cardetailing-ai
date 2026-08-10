from PIL import Image, ImageDraw, ImageFilter
import os

base = r"C:\Users\ZAHAR\cardetailing-ai\frontend\public\images"
src = Image.open(os.path.join(base, "login-car.jpg")).convert("RGB")
w, h = src.size
print("src", w, h)

# Save diagnostic strips
src.crop((0, 0, 80, h)).save(os.path.join(base, "_diag-left.jpg"), quality=90)
src.crop((w - 120, 0, w, int(h * 0.35))).save(os.path.join(base, "_diag-tr.jpg"), quality=90)
src.crop((0, 0, w, 100)).save(os.path.join(base, "_diag-top.jpg"), quality=90)

# Heuristic: find content box by looking for non-black from left
px = src.load()

def col_brightness(x):
    s = 0
    n = 0
    for y in range(0, h, 4):
        r, g, b = px[x, y]
        s += r + g + b
        n += 1
    return s / n

# Find left edge where brightness rises (past black phone bezel)
left = 0
for x in range(0, w // 4):
    if col_brightness(x) > 25:
        left = max(0, x - 2)
        break

right = w
for x in range(w - 1, w * 3 // 4, -1):
    if col_brightness(x) > 25:
        right = min(w, x + 2)
        break

# Top: skip header band if present (face/orb area often in first ~8-15%)
top = int(h * 0.02)
# If top-right has bright skin, cut more from top
def region_skin(x0, y0, x1, y1):
    c = 0
    t = 0
    for y in range(y0, y1, 2):
        for x in range(x0, x1, 2):
            r, g, b = px[x, y]
            t += 1
            if r > 90 and g > 55 and b > 40 and r > g + 10 and r > b + 15:
                c += 1
    return c / max(1, t)

skin_tr = region_skin(int(w * 0.75), 0, w, int(h * 0.2))
print("skin_tr ratio", round(skin_tr, 4), "left", left, "right", right)
if skin_tr > 0.01:
    top = max(top, int(h * 0.12))
    print("cutting top for face to", top)

# Also cut left more if phone buttons (bright-ish vertical blobs in left 3%)
left = max(left, int(w * 0.035))
right = min(right, int(w * 0.985))
bottom = int(h * 0.98)

clean = src.crop((left, top, right, bottom))
print("clean crop", (left, top, right, bottom), "->", clean.size)

# Darken extreme edges so they blend with black UI
out = clean.copy()
ow, oh = out.size
p = out.load()
for y in range(oh):
    for x in range(min(10, ow)):
        r, g, b = p[x, y]
        f = (x / 10) ** 0.7
        p[x, y] = (int(r * f), int(g * f), int(b * f))
    for x in range(max(0, ow - 10), ow):
        r, g, b = p[x, y]
        f = ((ow - 1 - x) / 10) ** 0.7
        p[x, y] = (int(r * f), int(g * f), int(b * f))

# top fade into black
for y in range(min(8, oh)):
    f = (y / 8) ** 0.6
    for x in range(ow):
        r, g, b = p[x, y]
        p[x, y] = (int(r * f), int(g * f), int(b * f))

out.save(os.path.join(base, "login-car.png"), optimize=True)
out.save(os.path.join(base, "bmw-x5-hero.jpg"), quality=93, optimize=True)
out.crop((out.width - 100, 0, out.width, 120)).save(os.path.join(base, "_clean-tr.png"))
out.crop((0, 0, 60, out.height)).save(os.path.join(base, "_clean-left.png"))
print("saved clean assets", out.size)

# Build a crisp sports-car logo PNG (silhouette) for header
logo = Image.new("RGBA", (168, 72), (0, 0, 0, 0))
d = ImageDraw.Draw(logo)
# body
gold = (212, 168, 75, 255)
gold_hi = (240, 217, 160, 255)
# sports coupe silhouette path via polygon
body = [
    (12, 44), (22, 34), (38, 28), (48, 16), (58, 12), (110, 12), (122, 18),
    (138, 28), (152, 34), (158, 42), (160, 50), (148, 52), (140, 48),
    (128, 52), (118, 48), (50, 48), (40, 52), (28, 48), (18, 52), (10, 48),
]
d.polygon(body, fill=gold)
# cabin glass darker
d.polygon([(56, 16), (72, 16), (68, 28), (52, 28)], fill=(20, 20, 20, 200))
d.polygon([(76, 16), (108, 16), (112, 28), (72, 28)], fill=(20, 20, 20, 180))
# wheels
d.ellipse([24, 42, 48, 66], outline=gold_hi, width=3, fill=(10, 10, 10, 255))
d.ellipse([120, 42, 144, 66], outline=gold_hi, width=3, fill=(10, 10, 10, 255))
d.ellipse([32, 50, 40, 58], fill=gold_hi)
d.ellipse([128, 50, 136, 58], fill=gold_hi)
logo = logo.filter(ImageFilter.SMOOTH_MORE)
logo.save(os.path.join(base, "header-car-logo.png"))
print("logo saved")
