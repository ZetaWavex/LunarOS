import math
import os
import socket
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
QEMU = os.path.join(ROOT, "Program", "QEMU", "qemu-system-i386.exe")
IMG = os.path.join(ROOT, "build", "os-image.img")
PORT = 5555


def mon(cmds, wait=0.2):
    s = socket.create_connection(("127.0.0.1", PORT), timeout=5)
    s.settimeout(1.5)
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
    mon(["screendump build/" + name + ".ppm"], wait=0.12)
    for _ in range(10):
        if os.path.exists(ppm) and os.path.getsize(ppm) > 0:
            return ppm
        time.sleep(0.15)
    return None


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
    w = h = 0
    imgs = []
    stamps = []
    t0 = time.time()
    for i in range(12):
        ppm = grab(f"_q{i}")
        if ppm:
            im = Image.open(ppm).convert("RGB")
            w, h = im.size
            imgs.append(im)
            stamps.append(time.time() - t0)
        time.sleep(0.02)

    try:
        mon(["quit"], wait=0.05)
    except Exception:
        pass
    time.sleep(0.3)
    if p.poll() is None:
        p.terminate()

    if len(imgs) < 3:
        print("too few frames")
        return 1

    cx, cy = w // 2, int(h * 0.683)

    def sector_angles(im):
        best = {}
        for yy in range(cy - 40, cy + 40):
            for xx in range(cx - 40, cx + 40):
                if 0 <= xx < w and 0 <= yy < h:
                    q = im.getpixel((xx, yy))
                    if q[0] > 120 and q[1] > 120 and q[2] > 120:
                        ang = math.degrees(math.atan2(yy - cy, xx - cx))
                        b = int((ang + 180) // 10) * 10 - 180
                        d = math.hypot(xx - cx, yy - cy)
                        if b not in best or d > best[b]:
                            best[b] = d
        return set(best.keys())

    print("frames:", len(imgs))
    prev = None
    for i, im in enumerate(imgs):
        sec = sector_angles(im)
        if prev is not None:
            only_prev = prev - sec
            only_cur = sec - prev
            a = sorted(only_prev)
            b = sorted(only_cur)
            print(f"t={stamps[i]:6.3f}  occupied={len(sec):2d}  "
                  f"gone={a[:4]} new={b[:4]}")
        else:
            print(f"t={stamps[i]:6.3f}  occupied={len(sec):2d}")
        prev = sec
    return 0


if __name__ == "__main__":
    sys.exit(main())