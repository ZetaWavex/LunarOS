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


def mon(cmds, wait=0.12):
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
    mon(["screendump build/" + name + ".ppm"])
    for _ in range(10):
        if os.path.exists(ppm) and os.path.getsize(ppm) > 0:
            return ppm
        time.sleep(0.1)
    return None


def ring_mask(im, cx, cy, rmin=8, rmax=30, step=1):
    w, h = im.size
    occ = [0] * 360
    tot = [0] * 360
    for yy in range(cy - rmax - 2, cy + rmax + 3, step):
        for xx in range(cx - rmax - 2, cx + rmax + 3, step):
            if not (0 <= xx < w and 0 <= yy < h):
                continue
            d = math.hypot(xx - cx, yy - cy)
            if d < rmin or d > rmax:
                continue
            a = int(math.degrees(math.atan2(yy - cy, xx - cx))) % 360
            tot[a] += 1
            p = im.getpixel((xx, yy))
            if p[0] > 120 and p[1] > 120 and p[2] > 120:
                occ[a] += 1
    return occ, tot


def best_shift(a, b):
    best_d = 0
    best_s = -1
    for d in range(0, 360):
        s = 0
        for i in range(360):
            j = (i + d) % 360
            s += min(a[i], b[j])
        if s > best_s:
            best_s = s
            best_d = d
    return best_d, best_s


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
    shots = []
    t0 = time.time()
    for i in range(6):
        ppm = grab(f"_r{i}")
        if ppm:
            im = Image.open(ppm).convert("RGB")
            shots.append((time.time() - t0, im))
        time.sleep(0.5)

    try:
        mon(["quit"], wait=0.05)
    except Exception:
        pass
    time.sleep(0.3)
    if p.poll() is None:
        p.terminate()

    if len(shots) < 2:
        print("too few")
        return 1

    w, h = shots[0][1].size
    cx, cy = w // 2, int(h * 0.683)
    print("frames:", len(shots), "center:", (cx, cy))

    masks = []
    for t, im in shots:
        occ, tot = ring_mask(im, cx, cy)
        masks.append((t, occ))

    base_t, base = masks[0]
    prev = 0
    cum = 0
    for t, occ in masks[1:]:
        d, score = best_shift(base, occ)
        step = (d - prev) % 360
        prev = d
        cum = d
        print(f"t={t:6.3f}  rel_shift={d:3d}deg  step={step:3d}deg  "
              f"score={score:4d}  est_rpm={cum/(t-base_t)*60/360:6.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())