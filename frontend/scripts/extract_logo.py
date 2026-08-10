from PIL import Image, ImageEnhance, ImageOps
import os

base = r"C:\Users\ZAHAR\cardetailing-ai\frontend\public\images"

# Ideal logo from user's "what should be" crop
ref1 = r"C:\Users\ZAHAR\.cursor\projects\c-Users-ZAHAR-cardetailing-ai\assets\c__Users_ZAHAR_AppData_Roaming_Cursor_User_workspaceStorage_empty-window_images_i-470ccbc0-09e0-4777-a79c-d018d17d9483.png"
im = Image.open(ref1).convert("RGBA")
w, h = im.size
print("ref1", w, h)

# Try several logo crops on left of title
for i, box in enumerate([
    (0, 20, 70, 90),
    (5, 30, 75, 85),
    (8, 35, 68, 82),
    (10, 40, 72, 88),
]):
    c = im.crop(box)
    c = c.resize((c.width * 3, c.height * 3), Image.Resampling.LANCZOS)
    path = os.path.join(base, f"logo-try-{i}.png")
    c.save(path)
    print(i, box, c.size)

# Also from larger second screenshot — find phone content left
ref2 = r"C:\Users\ZAHAR\.cursor\projects\c-Users-ZAHAR-cardetailing-ai\assets\c__Users_ZAHAR_AppData_Roaming_Cursor_User_workspaceStorage_empty-window_images________________667_-1097cb0a-af08-4456-b784-5336f3c6a283.png"
im2 = Image.open(ref2).convert("RGBA")
print("ref2", im2.size)
# phone roughly centered; logo near top of phone screen
# From description it's a full browser view - phone is center
rw, rh = im2.size
# Guess phone left ~35% of width based on typical layout
for i, box in enumerate([
    (int(rw*0.355), int(rh*0.12), int(rw*0.42), int(rh*0.20)),
    (int(rw*0.34), int(rh*0.10), int(rw*0.43), int(rh*0.22)),
    (int(rw*0.36), int(rh*0.13), int(rw*0.41), int(rh*0.19)),
]):
    c = im2.crop(box)
    c = c.resize((c.width * 2, c.height * 2), Image.Resampling.LANCZOS)
    path = os.path.join(base, f"logo2-try-{i}.png")
    c.save(path)
    print("2-", i, box, c.size)
