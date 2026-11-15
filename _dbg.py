import subprocess, time, os

QEMU = r"D:\NewX\OS\Try 5\Program\QEMU\qemu-system-i386.exe"
IMG = r"D:\NewX\OS\Try 5\build\os-image.img"

print("img exists:", os.path.exists(IMG), os.path.getsize(IMG) if os.path.exists(IMG) else -1)
print("qemu exists:", os.path.exists(QEMU))

p = subprocess.Popen(
    [QEMU, "-drive", "format=raw,file=" + IMG,
     "-monitor", "tcp:127.0.0.1:55630,server,nowait",
     "-serial", "file:D:\\NewX\\OS\\Try 5\\serial.log"],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
)
time.sleep(5)
print("poll:", p.poll())
if p.poll() is not None:
    out, err = p.communicate()
    print("OUT:", out.decode(errors="replace")[:3000])
    print("ERR:", err.decode(errors="replace")[:3000])
else:
    print("running ok")
    p.kill()