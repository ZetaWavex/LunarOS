import socket
import subprocess
import sys
import time
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
QEMU = os.path.join(ROOT, "Program", "QEMU", "qemu-system-x86_64.exe")
IMAGE = os.path.join(ROOT, "build", "os-image.img")
SERIAL = os.path.join(ROOT, "build", "serial.log")
MON = 45458


def main():
    if os.path.exists(SERIAL):
        os.remove(SERIAL)

    cmd = [
        QEMU, "-vga", "std", "-display", "none",
        "-drive", f"format=raw,file={IMAGE}",
        "-serial", f"file:{SERIAL}",
        "-monitor", f"tcp:127.0.0.1:{MON},server,nowait",
    ]
    p = subprocess.Popen(cmd, cwd=ROOT)
    time.sleep(1.0)

    s = socket.create_connection(("127.0.0.1", MON), timeout=5)
    time.sleep(0.3)
    s.recv(65536)

    def mon(c, wait=0.4):
        s.sendall(c.encode() + b"\n")
        time.sleep(wait)
        try:
            s.recv(65536)
        except Exception:
            pass

    time.sleep(9.5)

    for i in range(6):
        mon("mouse_move 5 6", 0.06)
    time.sleep(0.3)

    for k in ("1", "2", "3", "4"):
        mon(f"sendkey {k}", 0.2)
    time.sleep(0.4)
    mon("sendkey ret", 0.6)
    time.sleep(1.2)
    mon("screendump build\\c2.ppm", 0.8)

    s.close()
    p.terminate()
    time.sleep(1.2)

    with open(SERIAL, "r", encoding="utf-8", errors="ignore") as f:
        print(f.read())
    return 0


if __name__ == "__main__":
    sys.exit(main())