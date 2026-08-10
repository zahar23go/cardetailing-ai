from PIL import Image
import os

base = r"C:\Users\ZAHAR\cardetailing-ai\frontend\public\images"
ref1 = r"C:\Users\ZAHAR\.cursor\projects\c-Users-ZAHAR-cardetailing-ai\assets\c__Users_ZAHAR_AppData_Roaming_Cursor_User_workspaceStorage_empty-window_images_i-470ccbc0-09e0-4777-a79c-d018d17d9483.png"
im = Image.open(ref1).convert("RGB")
im.save(os.path.join(base, "_ref1-full.png"))
w, h = im.size
print(w, h)

# Find gold-ish pixels in left half
gold = []
for y in range(h):
    for x in range(w // 2):
        r, g, b = im.getpixel((x, y))
        if r > 140 and g > 100 and b < 120 and r > b + 40 and abs(r - g) < 60:
            gold.append((x, y))
if gold:
    xs = [p[0] for p in gold]
    ys = [p[1] for p in gold]
    print("gold bbox", min(xs), min(ys), max(xs), max(ys), "count", len(gold))
    pad = 4
    box = (max(0, min(xs) - pad), max(0, min(ys) - pad), min(w, max(xs) + pad), min(h, max(ys) + pad))
    logo = im.crop(box)
    # scale up
    logo = logo.resize((logo.width * 4, logo.height * 4), Image.Resampling.LANCZOS)
    logo.save(os.path.join(base, "header-car-logo.png"))
    print("saved logo", box, logo.size)
else:
    print("no gold found")
    # dump row averages
    for y in range(0, h, 10):
        row = [im.getpixel((x, y)) for x in range(0, min(100, w))]
        avg = tuple(sum(c[i] for c in row)//len(row) for i in range(3))
        print(y, avg)
