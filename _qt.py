import subprocess, time, os

QEMU = r"D:\NewX\OS\Try 5\Program\QEMU\qemu-system-i386.exe"
IMG = r"D:\NewX\OS\Try 5\build\os-image.bin"

p = subprocess.Popen(
    [QEMU, "-drive", "format=raw,file=" + IMG,
     "-monitor", "tcp:127.0.0.1:55610,server,nowait",
     "-serial", "file:D:\\NewX\\OS\\Try 5\\serial.log"],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
)
time.sleep(5)
print("poll:", p.poll())
try:
    out, err = p.communicate(timeout=3)
    print("OUT:", out.decode(errors="replace")[:2000])
    print("ERR:", err.decode(errors="replace")[:2000])
except subprocess.TimeoutExpired:
    print("still running -> kill")
    p.kill()