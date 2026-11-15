import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(ROOT, "build.py")
IMAGE = os.path.join(ROOT, "build", "os-image.img")
QEMU = os.path.join(ROOT, "Program", "QEMU", "qemu-system-i386.exe")

QEMU_PROCESSES = ("qemu-system-i386.exe", "qemu-system-x86_64.exe")
MAX_RETRY = 3


def banner(text):
    print("=" * 44)
    print(f" {text}")
    print("=" * 44)


def kill_qemu():
    for name in QEMU_PROCESSES:
        subprocess.run(["taskkill", "/F", "/IM", name],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)


def build():
    banner("Building image...")
    result = subprocess.run([sys.executable, BUILD], cwd=ROOT)
    return result.returncode == 0


def launch():
    cmd = [QEMU, "-drive", f"format=raw,file={IMAGE}"]
    for attempt in range(1, MAX_RETRY + 1):
        print()
        banner("Starting QEMU...")
        print(f"  {' '.join(cmd)}")
        code = subprocess.run(cmd, cwd=ROOT).returncode
        if code == 0:
            return True
        if attempt >= MAX_RETRY:
            break
        print()
        print(f"QEMU failed (attempt {attempt}/{MAX_RETRY}), retrying in 3s...")
        kill_qemu()
        time.sleep(3)
    return False


def main():
    kill_qemu()

    print()
    banner("Waiting for file handles to release...")
    time.sleep(2)

    if not build():
        print()
        print("BUILD FAILED!")
        return 1

    if not os.path.exists(IMAGE):
        print()
        print(f"IMAGE NOT FOUND: {IMAGE}")
        return 1

    if not os.path.exists(QEMU):
        print()
        print(f"QEMU NOT FOUND: {QEMU}")
        return 1

    if not launch():
        print()
        print(f"QEMU failed after {MAX_RETRY} attempts.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())