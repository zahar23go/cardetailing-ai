from PIL import Image

path = r"c:\Users\ZAHAR\AppData\Local\Temp\cursor\screenshots\main-check.png"
im = Image.open(path).convert("RGB")
print("size", im.size)
w, h = im.size
# brightness of whole image
pixels = list(im.getdata())
avg = tuple(sum(c[i] for c in pixels) // len(pixels) for i in range(3))
print("avg", avg)
# crop center phone area
cx0, cx1 = int(w * 0.15), int(w * 0.85)
cy0, cy1 = int(h * 0.02), int(h * 0.45)
top = im.crop((cx0, cy0, cx1, cy1))
out = r"C:\Users\ZAHAR\cardetailing-ai\frontend\public\images\_debug-main-top.png"
top.save(out)
print("saved", out, top.size)
# left strip of phone
left = im.crop((cx0, cy0, cx0 + 40, cy1))
left.save(r"C:\Users\ZAHAR\cardetailing-ai\frontend\public\images\_debug-main-left.png")
