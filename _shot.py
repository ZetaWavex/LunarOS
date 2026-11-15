import socket, time, struct, zlib, os, sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 55581
NAME = sys.argv[2] if len(sys.argv) > 2 else "shot"

ppm = r"D:\NewX\OS\Try 5\%s.ppm" % NAME
png = r"D:\NewX\OS\Try 5\%s.png" % NAME

if os.path.exists(ppm):
    os.remove(ppm)

s = socket.create_connection(("127.0.0.1", PORT))
s.sendall(('screendump "%s"\n' % ppm.replace("\\", "/")).encode())
time.sleep(1.5)
s.close()

for _ in range(30):
    if os.path.exists(ppm) and os.path.getsize(ppm) > 100:
        break
    time.sleep(0.1)

if not os.path.exists(ppm):
    print("ERROR: screendump produced no file")
    sys.exit(1)

data = open(ppm, "rb").read()
parts = data.split(b"\n", 3)
w, h = map(int, parts[1].split())
raw = parts[3]
rows = b"".join(b"\x00" + raw[y * w * 3:(y + 1) * w * 3] for y in range(h))


def chunk(t, x):
    return struct.pack(">I", len(x)) + t + x + struct.pack(">I", zlib.crc32(t + x) & 0xFFFFFFFF)


out = (b"\x89PNG\r\n\x1a\n"
       + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
       + chunk(b"IDAT", zlib.compress(rows, 9))
       + chunk(b"IEND", b""))
open(png, "wb").write(out)
print("OK %s %dx%d -> %s (%d bytes)" % (NAME, w, h, png, len(out)))