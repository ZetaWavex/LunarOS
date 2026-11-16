import os
import subprocess
import sys
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
BUILD = os.path.join(ROOT, "build")

NASM = r"d:\NewX\OS\Try 5\Program\NASM\nasm.exe"


def _find_mingw():
    cands = [
        r"D:\NewX\OS\Try 4\Program\MinGW64\bin",
        r"E:\ZTX\Program\MinGW64",
        r"D:\Program\Dev-Cpp\MinGW64\bin",
        r"C:\Program Files\Dev-Cpp\MinGW64\bin",
    ]
    for d in cands:
        gcc = os.path.join(d, "gcc.exe")
        oc = os.path.join(d, "objcopy.exe")
        if not (os.path.exists(gcc) and os.path.exists(oc)):
            continue
        libexec = os.path.join(os.path.dirname(d), "libexec", "gcc")
        if os.path.isdir(libexec):
            for _, _, files in os.walk(libexec):
                if "cc1.exe" in files:
                    return d
    return cands[0]


MINGW_BIN = _find_mingw()
GCC = os.path.join(MINGW_BIN, "gcc.exe")
OBJCOPY = os.path.join(MINGW_BIN, "objcopy.exe")

STAGE2_SECTORS = 10

def run(cmd, desc=""):
    print(f"[BUILD] {desc}")
    print(f"  {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print(f"[ERROR] {desc} failed!")
        sys.exit(1)

def clean():
    if os.path.exists(BUILD):
        shutil.rmtree(BUILD)
    os.makedirs(BUILD)
    print("[BUILD] Cleaned build directory")

def pad_to_sectors(path, sectors):
    with open(path, "rb") as f:
        data = f.read()
    target = sectors * 512
    if len(data) < target:
        data += b"\x00" * (target - len(data))
    with open(path, "wb") as f:
        f.write(data)
    return len(data)

def build():
    clean()

    run([NASM, "-f", "bin", os.path.join(SRC, "boot.asm"),
         "-o", os.path.join(BUILD, "boot.bin")],
        "Assembling MBR bootsector")

    run([NASM, "-f", "elf32", os.path.join(SRC, "kernel_entry.asm"),
         "-o", os.path.join(BUILD, "kernel_entry.o")],
        "Assembling kernel entry")

    cflags = [
        "-m32", "-ffreestanding", "-fno-pie", "-fno-stack-protector",
        "-fno-leading-underscore", "-nostdlib", "-std=c99",
        f"-I{SRC}", "-c",
    ]

    run([GCC] + cflags + [os.path.join(SRC, "graphics.c"),
         "-o", os.path.join(BUILD, "graphics.o")],
        "Compiling graphics.c")

    run([GCC] + cflags + [os.path.join(SRC, "kernel.c"),
         "-o", os.path.join(BUILD, "kernel.o")],
        "Compiling kernel.c")

    run([GCC, "-m32", "-nostdlib", "-nostartfiles",
         "-T", os.path.join(SRC, "link.ld"),
         "-o", os.path.join(BUILD, "kernel.elf"),
         os.path.join(BUILD, "kernel_entry.o"),
         os.path.join(BUILD, "kernel.o"),
         os.path.join(BUILD, "graphics.o")],
        "Linking kernel")

    run([OBJCOPY, "-O", "binary",
         "--only-section=.text",
         "--only-section=.rdata",
         "--only-section=.data",
         "--change-addresses=-0x10000",
         os.path.join(BUILD, "kernel.elf"),
         os.path.join(BUILD, "kernel.bin")],
        "Converting kernel to binary")

    kernel_size = os.path.getsize(os.path.join(BUILD, "kernel.bin"))
    kernel_sectors = (kernel_size + 511) // 512

    k_lba = 1 + STAGE2_SECTORS
    run([NASM, f"-DK_LBA={k_lba}", f"-DKERNEL_SECTORS={kernel_sectors}",
         "-f", "bin", "-i", SRC + "\\",
         os.path.join(SRC, "stage2.asm"),
         "-o", os.path.join(BUILD, "stage2.bin")],
        f"Assembling stage2 (KERNEL_SECTORS={kernel_sectors})")

    boot_size = os.path.getsize(os.path.join(BUILD, "boot.bin"))
    s2_size_before = os.path.getsize(os.path.join(BUILD, "stage2.bin"))

    pad_to_sectors(os.path.join(BUILD, "stage2.bin"), STAGE2_SECTORS)
    s2_size = os.path.getsize(os.path.join(BUILD, "stage2.bin"))

    with open(os.path.join(BUILD, "os-image.img"), "wb") as img:
        with open(os.path.join(BUILD, "boot.bin"), "rb") as f:
            img.write(f.read())
        with open(os.path.join(BUILD, "stage2.bin"), "rb") as f:
            img.write(f.read())
        with open(os.path.join(BUILD, "kernel.bin"), "rb") as f:
            img.write(f.read())
        written = img.tell()
        sector_rem = written % 512
        if sector_rem:
            img.write(b"\x00" * (512 - sector_rem))

    total = os.path.getsize(os.path.join(BUILD, "os-image.img"))
    print(f"\n[DONE] os-image.img: {total} bytes ({total//512} sectors)")
    print(f"  boot.bin:    {boot_size:>7} B  (MBR, LBA 0)")
    print(f"  stage2.bin:  {s2_size_before:>7} B -> padded {s2_size} B ({STAGE2_SECTORS} sectors, LBA 1-{STAGE2_SECTORS})")
    print(f"  kernel.bin:  {kernel_size:>7} B  ({kernel_sectors} sectors, LBA {k_lba}+)")
    if total % 512 == 0:
        print(f"  image aligned to 512-byte sectors: OK")

if __name__ == "__main__":
    build()