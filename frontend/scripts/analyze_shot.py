from PIL import Image
import os

path = r"c:\Users\ZAHAR\AppData\Local\Temp\cursor\screenshots\login-check.png"
im = Image.open(path)
print("size", im.size, "mode", im.mode)
# save a crop of top portion for inspection
w, h = im.size
top = im.crop((0, 0, w, int(h * 0.55)))
out = r"C:\Users\ZAHAR\cardetailing-ai\frontend\public\images\_debug-top.png"
top.save(out)
print("saved", out)

# check left edge brightness
px = im.convert("RGB").load()
for x in [0, 1, 2, 5, 10, 20, 40]:
    samples = [px[x, y] for y in range(h // 4, h // 2, 20)]
    avg = tuple(sum(s[i] for s in samples) // len(samples) for i in range(3))
    print(f"x={x} avg={avg}")
