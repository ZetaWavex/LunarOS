import os
import socket
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
QEMU = os.path.join(ROOT, "Program", "QEMU", "qemu-system-i386.exe")
IMG = os.path.join(ROOT, "build", "os-image.img")
PPM = os.path.join(ROOT, "build", "_dump.ppm")
PNG = os.path.join(ROOT, "build", "_dump.png")
PORT = 5555


def monitor(cmds, wait=0.4):
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


def main():
    if os.path.exists(PPM):
        os.remove(PPM)

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

    time.sleep(3)
    monitor(["screendump build/_dump.ppm"])
    for _ in range(10):
        if os.path.exists(PPM) and os.path.getsize(PPM) > 0:
            break
        time.sleep(0.3)

    try:
        monitor(["quit"], wait=0.1)
    except Exception:
        pass
    time.sleep(0.5)
    if p.poll() is None:
        p.terminate()

    if not os.path.exists(PPM):
        print("screendump failed, no ppm")
        return 1

    with open(PPM, "rb") as f:
        head = f.read(64).decode(errors="ignore").split()
    print("PPM header:", head[:4])

    try:
        from PIL import Image
        im = Image.open(PPM)
        print("size:", im.size, "mode:", im.mode)
        im.save(PNG)
        print("saved:", PNG)
    except Exception as e:
        print("PIL error:", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())