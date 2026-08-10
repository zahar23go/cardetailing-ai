from PIL import Image
import os

base = r"C:\Users\ZAHAR\cardetailing-ai\frontend\public\images"
src = Image.open(os.path.join(base, "login-car.jpg")).convert("RGB")
w, h = src.size
px = src.load()

# Print brightness every 20px from left
print("=== left brightness profile ===")
for x in range(0, 250, 10):
    vals = []
    for y in range(h // 5, 4 * h // 5, 5):
        r, g, b = px[x, y]
        vals.append((r + g + b) / 3)
    avg = sum(vals) / len(vals)
    print(f"x={x:3d} avg={avg:6.1f}")

print("=== top brightness profile ===")
for y in range(0, 200, 10):
    vals = []
    for x in range(w // 5, 4 * w // 5, 5):
        r, g, b = px[x, y]
        vals.append((r + g + b) / 3)
    avg = sum(vals) / len(vals)
    print(f"y={y:3d} avg={avg:6.1f}")

# Save grid of crops to find safe content
for i, box in enumerate([
    (140, 100, 1560, 760),
    (180, 120, 1520, 740),
    (200, 140, 1500, 720),
    (220, 100, 1480, 700),
]):
    c = src.crop(box)
    c.save(os.path.join(base, f"_safe-{i}.jpg"), quality=90)
    print("safe", i, box, c.size)

# Prefer studio photo without UI chrome if available
photo = Image.open(os.path.join(base, "bmw-x5-photo.jpg")).convert("RGB")
print("photo", photo.size)
# Crop center car, cut left margin and any right artifacts
pw, ph = photo.size
# cut ~8% left, ~5% right, ~5% top, ~8% bottom (UI text overlays)
pc = photo.crop((int(pw * 0.08), int(ph * 0.05), int(pw * 0.95), int(ph * 0.88)))
pc.save(os.path.join(base, "_photo-clean.jpg"), quality=92)
print("photo-clean", pc.size)
