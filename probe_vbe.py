import os
import socket
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
QEMU = os.path.join(ROOT, "Program", "QEMU", "qemu-system-i386.exe")
IMAGE = os.path.join(ROOT, "build", "os-image.img")
OUT = os.path.join(ROOT, "probe_out")

MON_PORT = 45554
SER_LOG = os.path.join(OUT, "serial.log")
SHOT = os.path.join(OUT, "screen.ppm")


def kill_qemu():
    for name in ("qemu-system-i386.exe", "qemu-system-x86_64.exe"):
        subprocess.run(["taskkill", "/F", "/IM", name],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)


def main():
    if not os.path.exists(IMAGE):
        print("image missing")
        return 1
    kill_qemu()
    time.sleep(1)
    os.makedirs(OUT, exist_ok=True)

    wait = float(sys.argv[1]) if len(sys.argv) > 1 else 9.0
    tag = sys.argv[2] if len(sys.argv) > 2 else "screen"
    keys = sys.argv[3] if len(sys.argv) > 3 else ""
    global SER_LOG, SHOT
    SER_LOG = os.path.join(OUT, tag + "_serial.log")
    SHOT = os.path.join(OUT, tag + ".ppm")

    for p in (SER_LOG, SHOT):
        if os.path.exists(p):
            os.remove(p)

    cmd = [
        QEMU,
        "-vga", "std",
        "-m", "32",
        "-display", "none",
        "-serial", "file:" + SER_LOG,
        "-monitor", "tcp:127.0.0.1:%d,server,nowait" % MON_PORT,
        "-drive", "format=raw,file=" + IMAGE,
    ]
    proc = subprocess.Popen(cmd, cwd=ROOT,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)

    time.sleep(wait)

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", MON_PORT))
        s.settimeout(3)
        time.sleep(0.3)
        try:
            s.recv(65536)
        except socket.timeout:
            pass
        for ch in keys.split():
            s.sendall(("sendkey %s\n" % ch).encode())
            time.sleep(0.35)
        if keys:
            time.sleep(2.0)
        if len(sys.argv) > 4:
            mx, my = sys.argv[4].split(",")
            s.sendall(("mouse_move %s %s\n" % (mx, my)).encode())
            time.sleep(1.0)
        s.sendall(('screendump "%s"\n' % SHOT.replace("\\", "/")).encode())
        time.sleep(2.5)
        s.close()
    except Exception as e:
        print("monitor error:", e)

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

    if os.path.exists(SER_LOG):
        with open(SER_LOG, "r", errors="ignore") as f:
            txt = f.read()
        for line in txt.splitlines():
            if line.startswith("[KERNEL]") or line.startswith("VBE mode"):
                print(line)
    else:
        print("(no serial log)")

    if os.path.exists(SHOT):
        with open(SHOT, "rb") as f:
            print("screendump:", SHOT, f.read(16).decode(errors="ignore").strip().replace("\n", " "))
    else:
        print("(no screendump)")

    return 0


if __name__ == "__main__":
    sys.exit(main())