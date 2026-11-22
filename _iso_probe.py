import os
import socket
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
QEMU = os.path.join(ROOT, "Program", "QEMU", "qemu-system-i386.exe")
ISO = os.path.join(ROOT, "build", "LunarOS.iso")
OUT = os.path.join(ROOT, "probe_out")
MON_PORT = 45555


def main():
    os.makedirs(OUT, exist_ok=True)
    tag = sys.argv[1] if len(sys.argv) > 1 else "iso"
    wait = float(sys.argv[2]) if len(sys.argv) > 2 else 12.0
    keys = sys.argv[3] if len(sys.argv) > 3 else ""
    ser = os.path.join(OUT, tag + "_serial.log")
    shot = os.path.join(OUT, tag + ".ppm")
    dbg = os.path.join(OUT, tag + "_seabios.log")
    for p in (ser, shot, dbg):
        if os.path.exists(p):
            os.remove(p)

    subprocess.run(["taskkill", "/F", "/IM", "qemu-system-i386.exe"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)

    cmd = [
        QEMU,
        "-vga", os.environ.get("PROBE_VGA", "std"),
        "-m", "32",
        "-display", "none",
        "-serial", "file:" + ser,
        "-chardev", "file,id=dbg,path=" + dbg,
        "-device", "isa-debugcon,iobase=0x402,chardev=dbg",
        "-monitor", "tcp:127.0.0.1:%d,server,nowait" % MON_PORT,
        "-cdrom", ISO,
        "-boot", "d",
    ]
    proc = subprocess.Popen(cmd, cwd=ROOT,
                            stdout=subprocess.DEVNULL,
                            stderr=open(os.path.join(OUT, tag + "_qemu.err"), "wb"))
    time.sleep(wait)
    print("qemu alive:", proc.poll() is None, "rc:", proc.poll())

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
        s.sendall(('screendump "%s"\n' % shot.replace("\\", "/")).encode())
        time.sleep(2)
        s.close()
    except Exception as e:
        print("monitor error:", e)

    proc.terminate()
    time.sleep(1)
    subprocess.run(["taskkill", "/F", "/IM", "qemu-system-i386.exe"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("--- serial ---")
    if os.path.exists(ser):
        with open(ser, "r", errors="replace") as f:
            print(f.read())
    else:
        print("(none)")
    print("--- screenshot ---")
    print("exists:", os.path.exists(shot))
    print("--- seabios ---")
    if os.path.exists(dbg):
        with open(dbg, "r", errors="replace") as f:
            print(f.read()[-6000:])
    else:
        print("(none)")


if __name__ == "__main__":
    main()