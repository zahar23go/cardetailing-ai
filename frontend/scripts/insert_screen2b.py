from PIL import Image, ImageDraw, ImageFilter
import os

base = r"C:\Users\ZAHAR\cardetailing-ai\frontend\public\images"
src = Image.open(os.path.join(base, "_src2.png")).convert("RGB")

# High-quality upscale
up = src.resize((src.width * 5, src.height * 5), Image.Resampling.LANCZOS)
uw, uh = up.size

# Remove left phone chrome (~3.5%) and slight right overscan
panel = up.crop((int(uw * 0.038), 0, int(uw * 0.995), uh))
pw, ph = panel.size

# Cover half-face avatar (top-right) with solid black
d = ImageDraw.Draw(panel)
# Face circle area
d.ellipse(
    [int(pw * 0.72), int(ph * -0.02), int(pw * 1.02), int(ph * 0.30)],
    fill=(0, 0, 0),
)
# Also cover any leftover sliver
d.rectangle([int(pw * 0.86), 0, pw, int(ph * 0.22)], fill=(0, 0, 0))

# Soft left edge blend to pure black (no grey line)
px = panel.load()
for y in range(ph):
    for x in range(min(8, pw)):
        r, g, b = px[x, y]
        f = (x / 8) ** 0.9
        px[x, y] = (int(r * f), int(g * f), int(b * f))

panel.save(os.path.join(base, "login-hero-banner.png"), optimize=True)
print("banner", panel.size)

# Car-only for main page (below header line)
car = panel.crop((0, int(ph * 0.22), pw, ph))
car.save(os.path.join(base, "login-car.png"), optimize=True)
car.save(os.path.join(base, "bmw-x5-hero.jpg"), quality=94, optimize=True)
print("car", car.size)

# Logo crop from original panel (before face paint is fine — logo is left)
logo_src = up.crop((int(uw * 0.045), int(uh * 0.02), int(uw * 0.175), int(uh * 0.20)))
# Trim to content: find non-black bbox
logo_src = logo_src.convert("RGBA")
datas = logo_src.getdata()
# keep as RGB on black for img tag
logo_src.convert("RGB").save(os.path.join(base, "header-car-logo.png"))
print("logo", logo_src.size)

# Preview strips
panel.crop((0, 0, 40, ph)).save(os.path.join(base, "_chk-left.png"))
panel.crop((int(pw * 0.7), 0, pw, int(ph * 0.28))).save(os.path.join(base, "_chk-tr.png"))
print("ok")
