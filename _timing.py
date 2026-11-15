import socket, time, math, os, sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 55590


def dump(name):
    ppm = r"D:\NewX\OS\Try 5\t_%s.ppm" % name
    if os.path.exists(ppm):
        os.remove(ppm)
    s = socket.create_connection(("127.0.0.1", PORT))
    s.sendall(('screendump "%s"\n' % ppm.replace("\\", "/")).encode())
    time.sleep(0.25)
    s.close()
    for _ in range(20):
        if os.path.exists(ppm) and os.path.getsize(ppm) > 100:
            return ppm
        time.sleep(0.05)
    return None


def segs(ppm):
    d = open(ppm, "rb").read()
    h = d.split(b"\n", 3)
    w, hh = map(int, h[1].split())
    raw = h[3]
    cx, cy = 400, 380
    pts = []
    for y in range(cy - 45, cy + 45):
        for x in range(cx - 45, cx + 45):
            if raw[(y * w + x) * 3] > 180:
                pts.append(int(math.degrees(math.atan2(y - cy, x - cx)) % 360))
    if not pts:
        return []
    pts.sort()
    runs = []
    s0 = pts[0]
    p = pts[0]
    for a in pts[1:]:
        if a - p > 5:
            runs.append((s0, p))
            s0 = a
        p = a
    runs.append((s0, p))
    return runs


t0 = time.time()
samples = []
for i in range(14):
    p = dump(i)
    if not p:
        print("frame %d: no dump" % i)
        continue
    r = segs(p)
    t = time.time() - t0
    print("%6.2fs  nseg=%d  starts=%s  spans=%s" % (
        t, len(r), [x[0] for x in r], [x[1] - x[0] + 1 for x in r]))
    samples.append((t, r))
    time.sleep(0.05)

if len(samples) >= 2:
    a = samples[0][1][0][0]
    b = samples[-1][1][0][0]
    dt = samples[-1][0] - samples[0][0]
    delta = (b - a) % 360
    if dt > 0:
        deg_per_s = delta / dt
        print("--- rotation: %.1f deg/s -> period %.2f s ---" % (
            deg_per_s, 360 / deg_per_s if deg_per_s else 0))