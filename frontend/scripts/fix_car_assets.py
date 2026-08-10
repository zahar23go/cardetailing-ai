from PIL import Image
import os

base = r"C:\Users\ZAHAR\cardetailing-ai\frontend\public\images"

im = Image.open(os.path.join(base, "login-car.png")).convert("RGB")
w, h = im.size
crop = im.crop((int(w * 0.75), 0, w, int(h * 0.18)))
pixels = list(crop.getdata())
avg = tuple(sum(c[i] for c in pixels) // len(pixels) for i in range(3))
print("login-car top-right avg", avg, "size", crop.size)

left = im.crop((0, 0, 8, h))
lp = list(left.getdata())
lavg = tuple(sum(c[i] for c in lp) // len(lp) for i in range(3))
print("login-car left8 avg", lavg)

src = Image.open(os.path.join(base, "login-car.jpg")).convert("RGB")
print("login-car.jpg", src.size)
sw, sh = src.size
trimmed = src.crop((int(sw * 0.012), int(sh * 0.01), int(sw * 0.995), int(sh * 0.99)))
out = trimmed.copy()
ow, oh = out.size
px = out.load()
for y in range(oh):
    for x in range(min(6, ow)):
        r, g, b = px[x, y]
        f = x / 6
        px[x, y] = (int(r * f), int(g * f), int(b * f))
    for x in range(max(0, ow - 6), ow):
        r, g, b = px[x, y]
        f = (ow - 1 - x) / 6
        px[x, y] = (int(r * f), int(g * f), int(b * f))

out.save(os.path.join(base, "login-car.png"), optimize=True)
out.save(os.path.join(base, "bmw-x5-hero.jpg"), quality=92, optimize=True)
print("saved trimmed", out.size)

refs = [
    r"C:\Users\ZAHAR\.cursor\projects\c-Users-ZAHAR-cardetailing-ai\assets\c__Users_ZAHAR_AppData_Roaming_Cursor_User_workspaceStorage_empty-window_images_i-470ccbc0-09e0-4777-a79c-d018d17d9483.png",
    r"C:\Users\ZAHAR\.cursor\projects\c-Users-ZAHAR-cardetailing-ai\assets\c__Users_ZAHAR_AppData_Roaming_Cursor_User_workspaceStorage_empty-window_images________________667_-1097cb0a-af08-4456-b784-5336f3c6a283.png",
]
for rpath in refs:
    if os.path.exists(rpath):
        rim = Image.open(rpath)
        print("ref", os.path.basename(rpath), rim.size)
        # crop logo area top-left of first reference
        rw, rh = rim.size
        logo = rim.crop((0, 0, int(rw * 0.22), int(rh * 0.28)))
        logo.save(os.path.join(base, "header-logo-from-ref.png"))
        print("saved header-logo-from-ref", logo.size)
