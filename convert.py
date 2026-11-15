import os
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(ROOT, "image")
SRC_DIR = os.path.join(ROOT, "src")

LOGOS = [
    ("logo.png", "logo", 256, 256),
]

def convert_png(name, var, w, h):
    img_path = os.path.join(IMAGE_DIR, name)
    img = Image.open(img_path).convert("RGBA")
    img = img.resize((w, h), Image.LANCZOS)
    pixels = list(img.getdata())

    c_path = os.path.join(SRC_DIR, f"{var}_data.h")
    with open(c_path, "w") as f:
        f.write(f"#ifndef {var.upper()}_DATA_H\n")
        f.write(f"#define {var.upper()}_DATA_H\n\n")
        f.write(f"#define {var.upper()}_W {w}\n")
        f.write(f"#define {var.upper()}_H {h}\n\n")
        f.write(f"typedef struct {{ unsigned char r,g,b,a; }} RGBA;\n\n")
        f.write(f"const RGBA {var}_pixels[{w * h}] = {{\n")

        for y in range(h):
            row = []
            for x in range(w):
                idx = y * w + x
                r, g, b, a = pixels[idx]
                row.append(f"{{{r},{g},{b},{a}}}")
            f.write("    " + ", ".join(row) + ",\n")

        f.write("};\n\n")
        f.write(f"#endif\n")

    print(f"[OK] {name} -> {c_path} ({w}x{h}, {w*h*4} bytes raw)")

if __name__ == "__main__":
    for name, var, w, h in LOGOS:
        convert_png(name, var, w, h)
    print("[DONE] All resources converted")