import os
import re
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
QEMU = os.path.join(ROOT, "Program", "QEMU", "qemu-system-i386.exe")
IMG = os.path.join(ROOT, "build", "os-image.img")
LOG = os.path.join(ROOT, "build", "_serial.log")


def main():
    if os.path.exists(LOG):
        os.remove(LOG)

    cmd = [QEMU, "-vga", "std", "-display", "none",
           "-serial", "file:" + LOG,
           "-drive", f"format=raw,file={IMG}"]
    p = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True,
                         encoding="utf-8", errors="ignore")
    time.sleep(20)
    if p.poll() is None:
        p.terminate()
    time.sleep(0.5)

    if not os.path.exists(LOG):
        print("no serial log")
        return 1

    data = open(LOG, "r", errors="ignore").read()
    mode = re.search(r"mode (\d+x\d+) (\d+)bpp", data)
    if mode:
        print("mode:", mode.group(1), mode.group(2) + "bpp")
    dots = data.count(".")
    span = 20.0
    print("total dots:", dots)
    print(f"frames/sec = {dots/span:.2f}   period = {span/dots*1000:.1f} ms")
    print("last line sample:", repr(data[-80:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())