from PIL import Image, ImageFilter, ImageEnhance
import os

base = r"C:\Users\ZAHAR\cardetailing-ai\frontend\public\images"
src = Image.open(os.path.join(base, "_src2.png")).convert("RGB")
w, h = src.size
print("src", w, h)

# Save full for reference
src.save(os.path.join(base, "ref-desired-header.png"))

# Upscale for quality
up = src.resize((w * 4, h * 4), Image.Resampling.LANCZOS)
uw, uh = up.size
print("up", uw, uh)

# Approximate regions on upscaled image (4x):
# left phone chrome ~0-3%
# header band ~0-22%
# face avatar top-right circle
# car content below header

# Logo: left of title in header
logo = up.crop((int(uw * 0.02), int(uh * 0.02), int(uw * 0.18), int(uh * 0.22)))
# make black bg transparent-ish by keeping as PNG on black
logo = logo.resize((logo.width * 2, logo.height * 2), Image.Resampling.LANCZOS)
logo.save(os.path.join(base, "header-car-logo.png"))
print("logo", logo.size)

# Hero: full width of phone content, below header, cut left chrome and right face remnant
# Cut left ~4%, right ~2% (face is in header so mainly cut top), top below header
hero = up.crop((
    int(uw * 0.04),   # past left phone border
    int(uh * 0.20),   # below header / face
    int(uw * 0.98),
    uh,
))
# Scale up further for crispness
hero = hero.resize((hero.width * 2, hero.height * 2), Image.Resampling.LANCZOS)
# Soft edge darken
p = hero.load()
ow, oh = hero.size
for y in range(oh):
    for x in range(min(12, ow)):
        r, g, b = p[x, y]
        f = (x / 12) ** 0.85
        p[x, y] = (int(r * f), int(g * f), int(b * f))
    for x in range(max(0, ow - 12), ow):
        r, g, b = p[x, y]
        f = ((ow - 1 - x) / 12) ** 0.85
        p[x, y] = (int(r * f), int(g * f), int(b * f))

hero.save(os.path.join(base, "login-car.png"), optimize=True)
hero.save(os.path.join(base, "bmw-x5-hero.jpg"), quality=94, optimize=True)
print("hero", hero.size)

# Also save a full-bleed banner: header strip WITHOUT face + car
# Black out the face region on the right of header in a combined banner
banner = up.copy()
# paint over face area (top-right circle) with black
from PIL import ImageDraw
d = ImageDraw.Draw(banner)
# face roughly at right
d.ellipse([int(uw * 0.78), int(uh * 0.0), int(uw * 1.05), int(uh * 0.28)], fill=(0, 0, 0))
# crop left chrome
banner = banner.crop((int(uw * 0.035), 0, uw, uh))
banner = banner.resize((banner.width * 2, banner.height * 2), Image.Resampling.LANCZOS)
banner.save(os.path.join(base, "login-hero-banner.png"), optimize=True)
print("banner", banner.size)
