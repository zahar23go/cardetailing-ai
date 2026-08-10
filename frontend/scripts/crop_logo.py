from PIL import Image
import os

base = r"C:\Users\ZAHAR\cardetailing-ai\frontend\public\images"
ref = r"C:\Users\ZAHAR\.cursor\projects\c-Users-ZAHAR-cardetailing-ai\assets\c__Users_ZAHAR_AppData_Roaming_Cursor_User_workspaceStorage_empty-window_images________________667_-1097cb0a-af08-4456-b784-5336f3c6a283.png"
im = Image.open(ref).convert("RGBA")
w, h = im.size
print("ref", w, h)

# Approximate phone content area — logo sits left of title in header
# Save several crops to inspect
crops = {
    "logo-a.png": (int(w * 0.28), int(h * 0.06), int(w * 0.40), int(h * 0.14)),
    "logo-b.png": (int(w * 0.30), int(h * 0.05), int(w * 0.42), int(h * 0.15)),
    "header-strip.png": (int(w * 0.26), int(h * 0.02), int(w * 0.74), int(h * 0.18)),
}
for name, box in crops.items():
    c = im.crop(box)
    c.save(os.path.join(base, name))
    print(name, box, c.size)
