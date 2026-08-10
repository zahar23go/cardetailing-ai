from PIL import Image, ImageDraw
import os

base = r"C:\Users\ZAHAR\cardetailing-ai\frontend\public\images"
src = Image.open(os.path.join(base, "_mock-phone.png")).convert("RGB")
w, h = src.size
print("mock", w, h)

# Upscale for quality
up = src.resize((w * 6, h * 6), Image.Resampling.LANCZOS)
uw, uh = up.size

# Car region: below header (~22%), full width, zoom to remove side gutters
car = up.crop((
    int(uw * 0.02),
    int(uh * 0.22),
    int(uw * 0.98),
    uh,
))
# Zoom in a bit more to fill phone edge-to-edge
cw, ch = car.size
car = car.crop((int(cw * 0.04), int(ch * 0.02), int(cw * 0.96), ch))
car = car.resize((car.width * 2, car.height * 2), Image.Resampling.LANCZOS)

# Soft black edge blend
px = car.load()
ow, oh = car.size
for y in range(oh):
    for x in range(min(8, ow)):
        r, g, b = px[x, y]
        f = (x / 8) ** 0.85
        px[x, y] = (int(r * f), int(g * f), int(b * f))
    for x in range(max(0, ow - 8), ow):
        r, g, b = px[x, y]
        f = ((ow - 1 - x) / 8) ** 0.85
        px[x, y] = (int(r * f), int(g * f), int(b * f))

car.save(os.path.join(base, "login-car.png"), optimize=True)
car.save(os.path.join(base, "bmw-x5-hero.jpg"), quality=95, optimize=True)
print("car", car.size)

# Logo: sports car outline from mockup header left
logo = up.crop((int(uw * 0.02), int(uh * 0.02), int(uw * 0.18), int(uh * 0.20)))
logo.save(os.path.join(base, "header-car-logo.png"))
print("logo", logo.size)
