from PIL import Image
import os

base = r"C:\Users\ZAHAR\cardetailing-ai\frontend\public\images"
src = Image.open(os.path.join(base, "_src2.png")).convert("RGB")
up = src.resize((src.width * 6, src.height * 6), Image.Resampling.LANCZOS)
uw, uh = up.size

# Full second screen as hero block, but:
# - cut left chrome
# - cut top header (logo/title/face) — HTML header will handle brand
# - keep only car
car = up.crop((
    int(uw * 0.045),  # past left border
    int(uh * 0.24),   # below header + face
    int(uw * 0.995),
    uh,
))

# Extra widen crop: scale content so edges are pure car bg
cw, ch = car.size
px = car.load()
for y in range(ch):
    for x in range(min(10, cw)):
        r, g, b = px[x, y]
        f = (x / 10) ** 0.9
        px[x, y] = (int(r * f), int(g * f), int(b * f))
    for x in range(max(0, cw - 10), cw):
        r, g, b = px[x, y]
        f = ((cw - 1 - x) / 10) ** 0.9
        px[x, y] = (int(r * f), int(g * f), int(b * f))

car.save(os.path.join(base, "login-car.png"), optimize=True)
car.save(os.path.join(base, "bmw-x5-hero.jpg"), quality=95, optimize=True)
print("car", car.size)

# Also save FULL second screen (no header cut) for optional banner use,
# with face painted carefully only on avatar circle without eating title
full = up.crop((int(uw * 0.04), 0, int(uw * 0.995), uh))
fw, fh = full.size
from PIL import ImageDraw
d = ImageDraw.Draw(full)
# tight circle on far right avatar only
cx, cy, r = int(fw * 0.92), int(fh * 0.11), int(fh * 0.11)
d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0, 0, 0))
full.save(os.path.join(base, "login-hero-banner.png"), optimize=True)
print("banner", full.size)
