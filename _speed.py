import os
import socket
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
QEMU = os.path.join(ROOT, "Program", "QEMU", "qemu-system-i386.exe")
IMG = os.path.join(ROOT, "build", "os-image.img")
PORT = 5555


def mon(cmds, wait=0.35):
    s = socket.create_connection(("127.0.0.1", PORT), timeout=5)
    s.settimeout(2)
    try:
        s.recv(4096)
    except socket.timeout:
        pass
    for c in cmds:
        s.sendall((c + "\n").encode())
        time.sleep(wait)
        try:
            s.recv(8192)
        except socket.timeout:
            pass
    s.close()


def grab(name):
    ppm = os.path.join(ROOT, "build", name + ".ppm")
    if os.path.exists(ppm):
        os.remove(ppm)
    mon(["screendump build/" + name + ".ppm"])
    for _ in range(8):
        if os.path.exists(ppm) and os.path.getsize(ppm) > 0:
            return ppm
        time.sleep(0.25)
    return None


def ring_angle(img):
    from PIL import Image
    w, h = img.size
    cx, cy = w // 2, int(h * 0.683)
    best = None
    tot = 0
    for yy in range(cy - 40, cy + 40):
        for xx in range(cx - 40, cx + 40):
            if 0 <= xx < w and 0 <= yy < h:
                p = img.getpixel((xx, yy))
                if p[0] > 120 and p[1] > 120 and p[2] > 120:
                    tot += 1
                    if best is None:
                        best = (xx, yy)
    return best, tot


def main():
    cmd = [QEMU, "-vga", "std", "-display", "none",
           "-monitor", f"tcp:127.0.0.1:{PORT},server,nowait",
           "-drive", f"format=raw,file={IMG}"]
    p = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True,
                         encoding="utf-8", errors="ignore")
    for _ in range(20):
        time.sleep(0.5)
        if p.poll() is not None:
            print("exited", p.returncode)
            print(p.communicate()[0])
            return 1
        try:
            socket.create_connection(("127.0.0.1", PORT), timeout=0.5).close()
            break
        except OSError:
            continue

    time.sleep(1.5)

    from PIL import Image
    import math
    seq = []
    t0 = time.time()
    for i in range(8):
        ppm = grab(f"_m{i}")
        if ppm:
            im = Image.open(ppm).convert("RGB")
            seq.append((time.time() - t0, im))
        time.sleep(0.15)

    try:
        mon(["quit"], wait=0.1)
    except Exception:
        pass
    time.sleep(0.4)
    if p.poll() is None:
        p.terminate()

    if not seq:
        print("no frames")
        return 1

    w, h = seq[0][1].size
    cx, cy = w // 2, int(h * 0.683)

    def centroid(im):
        sx = sy = n = 0
        for yy in range(cy - 40, cy + 40):
            for xx in range(cx - 40, cx + 40):
                if 0 <= xx < w and 0 <= yy < h:
                    p = im.getpixel((xx, yy))
                    if p[0] > 120 and p[1] > 120 and p[2] > 120:
                        sx += xx
                        sy += yy
                        n += 1
        if n == 0:
            return None
        return (sx / n - cx, sy / n - cy, n)

    print("frames:", len(seq), "size:", (w, h))
    prev = None
    for t, im in seq:
        c = centroid(im)
        if c is None:
            print(f"t={t:6.3f}  no ring")
            continue
        ang = math.degrees(math.atan2(c[1], c[0]))
        d = ""
        if prev is not None:
            dd = (ang - prev + 540) % 360 - 180
            d = f"  d_ang={dd:+7.2f}"
        print(f"t={t:6.3f}  n={c[2]:4d}  ang={ang:+7.2f}{d}")
        prev = ang
    return 0


if __name__ == "__main__":
    sys.exit(main())