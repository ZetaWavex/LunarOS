import subprocess, time, os, socket, struct, zlib

QEMU = r"D:\NewX\OS\Try 5\Program\QEMU\qemu-system-i386.exe"
IMG = r"D:\NewX\OS\Try 5\build\os-image.img"
LOG = r"D:\NewX\OS\Try 5\build\serial.log"
PORT = 55640

if os.path.exists(LOG):
    try:
        os.remove(LOG)
        print("removed old log")
    except Exception as e:
        print("cannot remove log:", e)

p = subprocess.Popen(
    [QEMU, "-drive", "format=raw,file=" + IMG,
     "-serial", "file:" + LOG,
     "-monitor", "tcp:127.0.0.1:%d,server,nowait" % PORT],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
time.sleep(6)
print("poll:", p.poll())

ppm = r"D:\NewX\OS\Try 5\build\check.ppm"
if os.path.exists(ppm):
    os.remove(ppm)
try:
    s = socket.create_connection(("127.0.0.1", PORT))
    s.sendall(('screendump "%s"\n' % ppm.replace("\\", "/")).encode())
    time.sleep(1.5)
    s.close()
except Exception as e:
    print("monitor connect failed:", e)

for _ in range(30):
    if os.path.exists(ppm) and os.path.getsize(ppm) > 100:
        break
    time.sleep(0.1)

if os.path.exists(ppm):
    d = open(ppm, "rb").read()
    h = d.split(b"\n", 3)
    w, hh = map(int, h[1].split())
    raw = h[3]
    rows = b"".join(b"\x00" + raw[y * w * 3:(y + 1) * w * 3] for y in range(hh))

    def chunk(t, x):
        return struct.pack(">I", len(x)) + t + x + struct.pack(">I", zlib.crc32(t + x) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, hh, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(rows, 9))
           + chunk(b"IEND", b""))
    open(r"D:\NewX\OS\Try 5\build\check.png", "wb").write(png)
    print("screenshot ok", w, hh)
else:
    print("no screenshot")

if os.path.exists(LOG):
    print("--- serial ---")
    print(open(LOG, encoding="utf-8", errors="replace").read().strip())

p.terminate()
time.sleep(0.5)
try:
    p.kill()
except Exception:
    pass