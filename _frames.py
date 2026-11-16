import os
import socket
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
QEMU = os.path.join(ROOT, "Program", "QEMU", "qemu-system-i386.exe")
IMG = os.path.join(ROOT, "build", "os-image.img")
PORT = 5555


def monitor(cmds, wait=0.5):
    s = socket.create_connection(("127.0.0.1", PORT), timeout=5)
    s.settimeout(3)
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


def shot(name):
    ppm = os.path.join(ROOT, "build", name + ".ppm")
    if os.path.exists(ppm):
        os.remove(ppm)
    monitor(["screendump build/" + name + ".ppm"])
    for _ in range(10):
        if os.path.exists(ppm) and os.path.getsize(ppm) > 0:
            break
        time.sleep(0.3)
    return ppm


def main():
    for f in ("_f1.png", "_f2.png", "_f3.png"):
        p = os.path.join(ROOT, "build", f)
        if os.path.exists(p):
            os.remove(p)

    cmd = [
        QEMU,
        "-vga", "std",
        "-display", "none",
        "-monitor", f"tcp:127.0.0.1:{PORT},server,nowait",
        "-drive", f"format=raw,file={IMG}",
    ]
    p = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True,
                         encoding="utf-8", errors="ignore")

    for _ in range(20):
        time.sleep(0.5)
        if p.poll() is not None:
            print("QEMU exited early rc=", p.returncode)
            print(p.communicate()[0])
            return 1
        try:
            socket.create_connection(("127.0.0.1", PORT), timeout=0.5).close()
            break
        except OSError:
            continue

    time.sleep(2.0)

    shots = []
    shots.append(shot("_f1"))
    time.sleep(0.05)
    shots.append(shot("_f2"))
    time.sleep(0.05)
    shots.append(shot("_f3"))

    try:
        monitor(["quit"], wait=0.1)
    except Exception:
        pass
    time.sleep(0.5)
    if p.poll() is None:
        p.terminate()

    from PIL import Image
    for i, ppm in enumerate(shots, 1):
        if not os.path.exists(ppm):
            print("missing", ppm)
            return 1
        im = Image.open(ppm)
        png = os.path.join(ROOT, "build", f"_f{i}.png")
        im.save(png)
        print(f"frame{i}: {im.size} -> {png}")
    return 0


if __name__ == "__main__":
    sys.exit(main())