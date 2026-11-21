import hashlib
import os
import struct
import subprocess
import sys
import shutil
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
BUILD = os.path.join(ROOT, "build")

NASM = r"d:\NewX\OS\Try 5\Program\NASM\nasm.exe"

DEFAULT_PASSWORD = "1234"
PWD_LBA = 256
PWD_FILE = "password.txt"


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


def make_password_file():
    encoded = hashlib.sha256(DEFAULT_PASSWORD.encode("utf-8")).hexdigest()
    path = os.path.join(BUILD, PWD_FILE)
    with open(path, "wb") as f:
        f.write(encoded.encode("ascii"))
    print(f"[BUILD] password file: {PWD_FILE} = {encoded}")
    print(f"  default password: {DEFAULT_PASSWORD}")
    return path


def parse_cur(path, want_size):
    with open(path, "rb") as f:
        data = f.read()

    reserved, ctype, count = struct.unpack("<HHH", data[0:6])
    if ctype != 2:
        raise ValueError(f"{path} is not a .cur file")

    for i in range(count):
        e = struct.unpack("<BBBBHHII", data[6 + i * 16:22 + i * 16])
        w, h, _colors, _res, hot_x, hot_y, _nbytes, off = e
        w = w or 256
        h = h or 256
        if w != want_size:
            continue

        hdr = struct.unpack("<IiiHHIIiiII", data[off:off + 40])
        _sz, _w, dh, _planes, bpp, comp = hdr[0], hdr[1], hdr[2], hdr[3], hdr[4], hdr[5]
        if comp != 0:
            raise ValueError(f"{path}: unsupported compression={comp}")

        px_w = w
        px_h = dh // 2
        base = off + 40
        out = bytearray(px_w * px_h * 4)

        if bpp == 32:
            for y in range(px_h):
                src_row = base + (px_h - 1 - y) * px_w * 4
                for x in range(px_w):
                    si = src_row + x * 4
                    b, g, r, a = data[si], data[si + 1], data[si + 2], data[si + 3]
                    di = (y * px_w + x) * 4
                    out[di] = r
                    out[di + 1] = g
                    out[di + 2] = b
                    out[di + 3] = a
            return w, px_h, hot_x, hot_y, bytes(out)

        if bpp == 24:
            stride = ((px_w * 3 + 3) // 4) * 4
            for y in range(px_h):
                src_row = base + (px_h - 1 - y) * stride
                for x in range(px_w):
                    si = src_row + x * 3
                    di = (y * px_w + x) * 4
                    out[di] = data[si + 2]
                    out[di + 1] = data[si + 1]
                    out[di + 2] = data[si]
                    out[di + 3] = 255
            return w, px_h, hot_x, hot_y, bytes(out)

        if bpp in (1, 4, 8):
            colors = 1 << bpp
            pal_off = base
            pal = []
            for c in range(colors):
                b, g, r, _a = data[pal_off + c * 4: pal_off + c * 4 + 4]
                pal.append((r, g, b))
            stride = ((px_w * bpp + 31) // 32) * 4
            xor_base = pal_off + colors * 4
            and_base = xor_base + stride * px_h
            and_stride = ((px_w + 31) // 32) * 4
            for y in range(px_h):
                src_row = xor_base + (px_h - 1 - y) * stride
                arow = and_base + (px_h - 1 - y) * and_stride
                for x in range(px_w):
                    a_bit = (data[arow + (x >> 3)] >> (7 - (x & 7))) & 1
                    di = (y * px_w + x) * 4
                    if a_bit:
                        out[di + 3] = 0
                        continue
                    if bpp == 8:
                        idx = data[src_row + x]
                    elif bpp == 4:
                        byte = data[src_row + (x >> 1)]
                        idx = (byte >> 4) if (x & 1) == 0 else (byte & 0x0F)
                    else:
                        byte = data[src_row + (x >> 3)]
                        idx = (byte >> (7 - (x & 7))) & 1
                    r, g, b = pal[idx]
                    out[di] = r
                    out[di + 1] = g
                    out[di + 2] = b
                    out[di + 3] = 255
            return w, px_h, hot_x, hot_y, bytes(out)

        raise ValueError(f"{path}: unsupported bpp={bpp}")

    raise ValueError(f"{path}: no {want_size}x{want_size} entry")


def crop_to_content(w, h, pixels):
    minx, miny, maxx, maxy = w, h, -1, -1
    for y in range(h):
        for x in range(w):
            if pixels[(y * w + x) * 4 + 3]:
                if x < minx:
                    minx = x
                if x > maxx:
                    maxx = x
                if y < miny:
                    miny = y
                if y > maxy:
                    maxy = y
    if maxx < 0:
        return 0, 0, w, h, pixels

    cw = maxx - minx + 1
    ch = maxy - miny + 1
    out = bytearray(cw * ch * 4)
    for y in range(ch):
        src = ((miny + y) * w + minx) * 4
        out[y * cw * 4:(y + 1) * cw * 4] = pixels[src:src + cw * 4]
    return minx, miny, cw, ch, bytes(out)


def emit_cursor(lines, prefix, w, h, hx, hy, pixels):
    lines.append(f"#define CURSOR_{prefix}_W {w}")
    lines.append(f"#define CURSOR_{prefix}_H {h}")
    lines.append(f"#define CURSOR_{prefix}_HOTX {hx}")
    lines.append(f"#define CURSOR_{prefix}_HOTY {hy}")
    lines.append(f"static const unsigned char cursor_{prefix.lower()}_rgba[{w * h * 4}] = {{")
    row = []
    for v in pixels:
        row.append(f"{v}")
        if len(row) == 20:
            lines.append("    " + ",".join(row) + ",")
            row = []
    if row:
        lines.append("    " + ",".join(row) + ",")
    lines.append("};")
    lines.append("")


def make_cursor_header():
    arrow_src = os.path.join(ROOT, "image", "Cursors", "aero_arrow.cur")
    beam_src = os.path.join(ROOT, "image", "Cursors", "beam_i.cur")
    link_src = os.path.join(ROOT, "image", "Cursors", "aero_link.cur")

    aw, ah, ahx, ahy, apx = parse_cur(arrow_src, 32)

    bw, bh, bhx, bhy, bpx = parse_cur(beam_src, 128)
    _, _, bw, bh, bpx = crop_to_content(bw, bh, bpx)
    bhx = bw // 2
    bhy = bh // 2

    lw, lh, lhx, lhy, lpx = parse_cur(link_src, 32)

    lines = [
        "/* generated by build.py from image/Cursors "
        "(aero_arrow.cur, beam_i.cur, aero_link.cur) */",
        "#ifndef CURSOR_DATA_H",
        "#define CURSOR_DATA_H",
        "",
    ]
    emit_cursor(lines, "ARROW", aw, ah, ahx, ahy, apx)
    emit_cursor(lines, "BEAM", bw, bh, bhx, bhy, bpx)
    emit_cursor(lines, "LINK", lw, lh, lhx, lhy, lpx)
    lines.append(f"#define CURSOR_MAX_W {max(aw, bw, lw)}")
    lines.append(f"#define CURSOR_MAX_H {max(ah, bh, lh)}")
    lines.append("")
    lines.append("#endif")

    path = os.path.join(BUILD, "cursor_data.h")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[BUILD] cursor header: {os.path.basename(path)} "
          f"(arrow {aw}x{ah} hot {ahx},{ahy}; beam {bw}x{bh} hot {bhx},{bhy})")
    return path

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
        f"-I{SRC}", f"-I{BUILD}", "-c",
    ]

    run([GCC] + cflags + [os.path.join(SRC, "graphics.c"),
         "-o", os.path.join(BUILD, "graphics.o")],
        "Compiling graphics.c")

    make_cursor_header()

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
    if k_lba + kernel_sectors > PWD_LBA:
        print(f"[ERROR] kernel overlaps password sector "
              f"(kernel ends at LBA {k_lba + kernel_sectors}, PWD_LBA={PWD_LBA})")
        sys.exit(1)
    run([NASM, f"-DK_LBA={k_lba}", f"-DKERNEL_SECTORS={kernel_sectors}",
         "-f", "bin", "-i", SRC + "\\",
         os.path.join(SRC, "stage2.asm"),
         "-o", os.path.join(BUILD, "stage2.bin")],
        f"Assembling stage2 (KERNEL_SECTORS={kernel_sectors})")

    boot_size = os.path.getsize(os.path.join(BUILD, "boot.bin"))
    s2_size_before = os.path.getsize(os.path.join(BUILD, "stage2.bin"))

    pad_to_sectors(os.path.join(BUILD, "stage2.bin"), STAGE2_SECTORS)
    s2_size = os.path.getsize(os.path.join(BUILD, "stage2.bin"))

    pwd_path = make_password_file()

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

        pwd_lba_off = PWD_LBA * 512
        cur = img.tell()
        if cur < pwd_lba_off:
            img.write(b"\x00" * (pwd_lba_off - cur))
        with open(pwd_path, "rb") as f:
            data = f.read()
        img.write(data)
        if len(data) < 512:
            img.write(b"\x00" * (512 - len(data)))

    total = os.path.getsize(os.path.join(BUILD, "os-image.img"))
    print(f"\n[DONE] os-image.img: {total} bytes ({total//512} sectors)")
    print(f"  boot.bin:    {boot_size:>7} B  (MBR, LBA 0)")
    print(f"  stage2.bin:  {s2_size_before:>7} B -> padded {s2_size} B ({STAGE2_SECTORS} sectors, LBA 1-{STAGE2_SECTORS})")
    print(f"  kernel.bin:  {kernel_size:>7} B  ({kernel_sectors} sectors, LBA {k_lba}+)")
    print(f"  {PWD_FILE}: {os.path.getsize(pwd_path):>6} B  (LBA {PWD_LBA})")
    if total % 512 == 0:
        print(f"  image aligned to 512-byte sectors: OK")

if __name__ == "__main__":
    build()