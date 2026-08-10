from PIL import Image, ImageDraw
import os

base = r"C:\Users\ZAHAR\cardetailing-ai\frontend\public\images"
src = Image.open(os.path.join(base, "_src2.png")).convert("RGB")
up = src.resize((src.width * 6, src.height * 6), Image.Resampling.LANCZOS)
uw, uh = up.size

# Source has inset car with grey gutters — zoom into content:
# left past phone chrome AND past grey gutter (~12%)
# right past grey gutter (~4%)
# keep header but cover face
full = up.crop((int(uw * 0.10), 0, int(uw * 0.96), uh))
fw, fh = full.size
d = ImageDraw.Draw(full)
cx, cy, r = int(fw * 0.93), int(fh * 0.12), int(fh * 0.13)
d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0, 0, 0))
# ensure right edge clean
d.rectangle([int(fw * 0.94), 0, fw, int(fh * 0.26)], fill=(0, 0, 0))

# Fade left to black
px = full.load()
for y in range(fh):
    for x in range(min(6, fw)):
        r_, g, b = px[x, y]
        f = (x / 6) ** 0.85
        px[x, y] = (int(r_ * f), int(g * f), int(b * f))

full.save(os.path.join(base, "login-hero-banner.png"), optimize=True)
print("banner", full.size)

# Car only for main
car = full.crop((0, int(fh * 0.26), fw, fh))
car.save(os.path.join(base, "login-car.png"), optimize=True)
car.save(os.path.join(base, "bmw-x5-hero.jpg"), quality=95, optimize=True)
print("car", car.size)
