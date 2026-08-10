from PIL import Image
import os
base = r"C:\Users\ZAHAR\cardetailing-ai\frontend\public\images"
im = Image.open(os.path.join(base, "login-car.png")).convert("RGB")
w, h = im.size
px = im.load()
print("size", w, h)
for x in [0, 5, 10, 20]:
    vals = [(sum(px[x, y]) / 3) for y in range(0, h, 8)]
    print(f"left x={x} avg={sum(vals)/len(vals):.1f}")
# top-right skin
skin = 0
total = 0
for y in range(0, min(80, h), 2):
    for x in range(max(0, w - 100), w, 2):
        r, g, b = px[x, y]
        total += 1
        if r > 90 and g > 55 and b > 40 and r > g + 10 and r > b + 15:
            skin += 1
print(f"tr skin {skin}/{total} ({100*skin/max(1,total):.2f}%)")
