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
        time.sleep(0.2)
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
    frames = []
    t0 = time.time()
    for i in range(10):
        ppm = grab(f"_s{i}")
        if ppm:
            frames.append((time.time() - t0, Image.open(ppm).convert("RGB")))
        time.sleep(0.12)

    try:
        mon(["quit"], wait=0.1)
    except Exception:
        pass
    time.sleep(0.4)
    if p.poll() is None:
        p.terminate()

    if not frames:
        print("no frames")
        return 1

    w, h = frames[0][1].size
    cx, cy = w // 2, int(h * 0.683)

    def ring_pixels(im):
        pts = []
        for yy in range(cy - 45, cy + 45):
            for xx in range(cx - 45, cx + 45):
                if 0 <= xx < w and 0 <= yy < h:
                    q = im.getpixel((xx, yy))
                    if q[0] > 120 and q[1] > 120 and q[2] > 120:
                        pts.append((xx, yy))
        return pts

    def top_angle(pts):
        if not pts:
            return None
        top = min(pts, key=lambda t: t[1])
        return math.degrees(math.atan2(top[1] - cy, top[0] - cx))

    print("frames:", len(frames), "size:", (w, h))
    prev = None
    prev_pts = None
    for t, im in frames:
        pts = ring_pixels(im)
        ang = top_angle(pts)
        diff = ""
        if prev_pts is not None:
            s1 = set(prev_pts)
            s2 = set(pts)
            diff = f"  changed={len(s1 ^ s2):4d}"
        a = f"{ang:+7.2f}" if ang is not None else "   n/a"
        print(f"t={t:6.3f}  n={len(pts):4d}  top_ang={a}{diff}")
        prev = ang
        prev_pts = pts
    return 0


if __name__ == "__main__":
    sys.exit(main())