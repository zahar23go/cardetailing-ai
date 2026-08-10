from PIL import Image
import os

base = r"C:\Users\ZAHAR\cardetailing-ai\frontend\public\images"
im = Image.open(os.path.join(base, "bmw-x5-hero.jpg")).convert("RGB")
w, h = im.size
print("hero", w, h)

# Right edge strip
right = im.crop((w - 80, 0, w, int(h * 0.35)))
right.save(os.path.join(base, "_hero-right.png"))
# Top strip
top = im.crop((0, 0, w, 60))
top.save(os.path.join(base, "_hero-top.png"))
# Left strip  
left = im.crop((0, 0, 40, h))
left.save(os.path.join(base, "_hero-left.png"))

# Count skin-like pixels in top-right
tr = im.crop((int(w*0.7), 0, w, int(h*0.25)))
skin = 0
total = 0
for r, g, b in tr.getdata():
    total += 1
    if r > 80 and g > 50 and b > 40 and r > g and r > b and abs(r - g) > 15:
        skin += 1
print(f"top-right skin-like {skin}/{total} ({100*skin/total:.2f}%)")

# Also check login-car
im2 = Image.open(os.path.join(base, "login-car.png")).convert("RGB")
w2, h2 = im2.size
tr2 = im2.crop((int(w2*0.7), 0, w2, int(h2*0.25)))
skin2 = 0
total2 = 0
for r, g, b in tr2.getdata():
    total2 += 1
    if r > 80 and g > 50 and b > 40 and r > g and r > b and abs(r - g) > 15:
        skin2 += 1
print(f"login top-right skin-like {skin2}/{total2} ({100*skin2/total2:.2f}%)")
print("login", w2, h2)
