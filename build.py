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
LD = os.path.join(MINGW_BIN, "ld.exe")
OBJCOPY = os.path.join(MINGW_BIN, "objcopy.exe")

STAGE2_SECTORS = 10
STAGE2_LBA = 10
KERNEL_LBA = 66

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

ISO_BLOCK = 2048

ISO_PVD_LBA = 16
ISO_BOOTREC_LBA = 17
ISO_TERM_LBA = 18
ISO_CATALOG_LBA = 19
ISO_PATHL_LBA = 20
ISO_PATHM_LBA = 21
ISO_ROOT_LBA = 22
ISO_IMAGE_LBA = 23

BOOT_MEDIA_HD = 4
BOOT_MEDIA_NONE = 0

ISO_USE_NONE = True


def _iso_time7():
    now = time.gmtime()
    return bytes([now.tm_year - 1900, now.tm_mon, now.tm_mday,
                  now.tm_hour, now.tm_min, now.tm_sec, 0])


def _both16(v):
    return struct.pack("<H", v) + struct.pack(">H", v)


def _both32(v):
    return struct.pack("<I", v) + struct.pack(">I", v)


def _iso_dir_record(extent, size, name, flags, when):
    body = bytearray()
    body += _both32(extent)
    body += _both32(size)
    body += when
    body.append(flags)
    body.append(0)
    body.append(0)
    body += _both16(1)
    body.append(len(name))
    body += name
    total = 2 + len(body)
    if total % 2:
        body.append(0)
        total += 1
    return bytes(bytearray([total, 0]) + body)


def _iso_pvd(volume_blocks, root_rec, path_size, when):
    pvd = bytearray(ISO_BLOCK)
    pvd[0] = 1
    pvd[1:6] = b"CD001"
    pvd[6] = 1
    pvd[40:72] = b"LUNAROS" + b"\x00" * (32 - 7)
    pvd[80:88] = _both32(volume_blocks)
    pvd[120:124] = _both16(1)
    pvd[124:128] = _both16(1)
    pvd[128:132] = _both16(ISO_BLOCK)
    pvd[132:140] = _both32(path_size)
    pvd[140:144] = struct.pack("<I", ISO_PATHL_LBA)
    pvd[144:148] = struct.pack("<I", 0)
    pvd[148:152] = struct.pack(">I", ISO_PATHM_LBA)
    pvd[152:156] = struct.pack(">I", 0)
    pvd[156:190] = root_rec
    pvd[190:318] = b"LUNAROS" + b"\x00" * (128 - 7)
    pvd[318:446] = b"\x00" * 128
    pvd[446:574] = b"\x00" * 128
    pvd[574:702] = b"\x00" * 128
    pvd[702:739] = b"\x00" * 37
    pvd[739:776] = b"\x00" * 37
    pvd[776:813] = b"\x00" * 37
    d17 = b"2026010100000000\x00"
    pvd[813:830] = d17
    pvd[830:847] = d17
    pvd[847:864] = b"\x00" * 17
    pvd[864:881] = b"\x00" * 17
    pvd[881] = 1
    return bytes(pvd)


def _iso_boot_record():
    br = bytearray(ISO_BLOCK)
    br[0] = 0
    br[1:6] = b"CD001"
    br[6] = 1
    ident = b"EL TORITO SPECIFICATION"
    br[7:39] = ident + b"\x00" * (32 - len(ident))
    br[71:75] = struct.pack("<I", ISO_CATALOG_LBA)
    return bytes(br)


def _iso_terminator():
    term = bytearray(ISO_BLOCK)
    term[0] = 255
    term[1:6] = b"CD001"
    term[6] = 1
    return bytes(term)


def _iso_boot_catalog(image_lba, boot_sectors):
    cat = bytearray(ISO_BLOCK)
    cat[0] = 1
    cat[1] = 0
    cat[30] = 0x55
    cat[31] = 0xAA
    words = 0
    for i in range(0, 32, 2):
        words += cat[i] | (cat[i + 1] << 8)
    cat[28:30] = struct.pack("<H", (-words) & 0xFFFF)

    e = 32
    cat[e] = 0x88
    if ISO_USE_NONE:
        cat[e + 1] = BOOT_MEDIA_NONE
        cat[e + 2:e + 4] = struct.pack("<H", 0x07C0)
        cat[e + 4] = 0
        cat[e + 5] = 0
        cat[e + 6:e + 8] = struct.pack("<H", boot_sectors & 0xFFFF)
        cat[e + 8:e + 12] = struct.pack("<I", image_lba)
    else:
        cat[e + 1] = BOOT_MEDIA_HD
        cat[e + 2:e + 4] = struct.pack("<H", 0)
        cat[e + 4] = 0
        cat[e + 5] = 0
        cat[e + 6:e + 8] = struct.pack("<H", boot_sectors)
        cat[e + 8:e + 12] = struct.pack("<I", image_lba)
    return bytes(cat)


def _iso_path_table(lba, big):
    rec = bytearray()
    rec.append(1)
    rec.append(0)
    rec += struct.pack(">I" if big else "<I", lba)
    rec += struct.pack(">H" if big else "<H", 1)
    rec.append(0)
    if len(rec) % 2:
        rec.append(0)
    return bytes(rec)


def make_iso(img_path, iso_path):
    with open(img_path, "rb") as f:
        raw = f.read()
    boot_img = raw
    if len(boot_img) % 512:
        boot_img += b"\x00" * (512 - len(boot_img) % 512)
    boot_sectors = len(boot_img) // 512
    if len(boot_img) % ISO_BLOCK:
        boot_img += b"\x00" * (ISO_BLOCK - len(boot_img) % ISO_BLOCK)

    when = _iso_time7()
    image_blocks = len(boot_img) // ISO_BLOCK
    volume_blocks = ISO_IMAGE_LBA + image_blocks

    root_rec = _iso_dir_record(ISO_ROOT_LBA, ISO_BLOCK, b"\x00", 2, when)
    path_l = _iso_path_table(ISO_ROOT_LBA, False)
    path_m = _iso_path_table(ISO_ROOT_LBA, True)
    path_size = len(path_l)

    root_dir = bytearray()
    root_dir += _iso_dir_record(ISO_ROOT_LBA, ISO_BLOCK, b"\x00", 2, when)
    root_dir += _iso_dir_record(ISO_ROOT_LBA, ISO_BLOCK, b"\x01", 2, when)
    if len(root_dir) > ISO_BLOCK:
        print("[ERROR] root directory exceeds one block")
        sys.exit(1)
    root_dir += b"\x00" * (ISO_BLOCK - len(root_dir))

    sectors = []
    sectors += [b"\x00" * ISO_BLOCK] * ISO_PVD_LBA
    sectors.append(_iso_pvd(volume_blocks, root_rec, path_size, when))
    sectors.append(_iso_boot_record())
    sectors.append(_iso_terminator())
    sectors.append(_iso_boot_catalog(ISO_IMAGE_LBA, boot_sectors))
    sectors.append(path_l + b"\x00" * (ISO_BLOCK - len(path_l)))
    sectors.append(path_m + b"\x00" * (ISO_BLOCK - len(path_m)))
    sectors.append(bytes(root_dir))
    for i in range(0, len(boot_img), ISO_BLOCK):
        sectors.append(boot_img[i:i + ISO_BLOCK])

    with open(iso_path, "wb") as f:
        for s in sectors:
            f.write(s)

    total = os.path.getsize(iso_path)
    print(f"[ISO] {os.path.basename(iso_path)}: {total} bytes "
          f"({len(sectors)} blocks)")
    print(f"  El Torito: hard-disk emulation, {boot_sectors} sectors, "
          f"boot image at block {ISO_IMAGE_LBA}")
    return iso_path


def build():
    clean()

    run([NASM, "-f", "bin", os.path.join(SRC, "boot.asm"),
         "-o", os.path.join(BUILD, "boot.bin")],
        "Assembling MBR bootsector")

    run([NASM, "-f", "elf64", os.path.join(SRC, "kernel_entry.asm"),
         "-o", os.path.join(BUILD, "kernel_entry.o")],
        "Assembling kernel entry (64-bit)")

    cflags = [
        "-m64", "-ffreestanding", "-fno-pie", "-fno-stack-protector",
        "-fno-leading-underscore", "-nostdlib", "-std=c99",
        "-mno-red-zone", "-mcmodel=small", "-mno-stack-arg-probe",
        "-fno-asynchronous-unwind-tables", "-fno-unwind-tables",
        f"-I{SRC}", f"-I{BUILD}", "-c",
    ]

    run([GCC] + cflags + [os.path.join(SRC, "graphics.c"),
         "-o", os.path.join(BUILD, "graphics.o")],
        "Compiling graphics.c")

    make_cursor_header()

    run([GCC] + cflags + [os.path.join(SRC, "kernel.c"),
         "-o", os.path.join(BUILD, "kernel.o")],
        "Compiling kernel.c")

    run([LD, "-m", "i386pep", "--image-base", "0x0", "-e", "start",
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

    if KERNEL_LBA + kernel_sectors > PWD_LBA:
        print(f"[ERROR] kernel overlaps password sector "
              f"(kernel ends at LBA {KERNEL_LBA + kernel_sectors}, PWD_LBA={PWD_LBA})")
        sys.exit(1)
    run([NASM, "-f", "bin", "-i", SRC + "\\",
         os.path.join(SRC, "stage2.asm"),
         "-o", os.path.join(BUILD, "stage2.bin")],
        "Assembling stage2")

    boot_size = os.path.getsize(os.path.join(BUILD, "boot.bin"))
    s2_size_before = os.path.getsize(os.path.join(BUILD, "stage2.bin"))

    pad_to_sectors(os.path.join(BUILD, "stage2.bin"), STAGE2_SECTORS)
    s2_size = os.path.getsize(os.path.join(BUILD, "stage2.bin"))

    pwd_path = make_password_file()

    with open(os.path.join(BUILD, "os-image.img"), "wb") as img:
        with open(os.path.join(BUILD, "boot.bin"), "rb") as f:
            img.write(f.read())

        stage2_off = STAGE2_LBA * 512
        cur = img.tell()
        if cur < stage2_off:
            img.write(b"\x00" * (stage2_off - cur))
        with open(os.path.join(BUILD, "stage2.bin"), "rb") as f:
            img.write(f.read())

        kernel_off = KERNEL_LBA * 512
        cur = img.tell()
        if cur > kernel_off:
            print(f"[ERROR] stage2 overflows past kernel LBA {KERNEL_LBA}")
            sys.exit(1)
        if cur < kernel_off:
            img.write(b"\x00" * (kernel_off - cur))
        with open(os.path.join(BUILD, "kernel.bin"), "rb") as f:
            img.write(f.read())

        pwd_lba_off = PWD_LBA * 512
        cur = img.tell()
        if cur > pwd_lba_off:
            print(f"[ERROR] kernel overflows past password LBA {PWD_LBA}")
            sys.exit(1)
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
    print(f"  stage2.bin:  {s2_size_before:>7} B -> padded {s2_size} B (LBA {STAGE2_LBA}-{STAGE2_LBA + STAGE2_SECTORS - 1})")
    print(f"  kernel.bin:  {kernel_size:>7} B  ({kernel_sectors} sectors, LBA {KERNEL_LBA}+)")
    print(f"  {PWD_FILE}: {os.path.getsize(pwd_path):>6} B  (LBA {PWD_LBA})")
    if total % 512 == 0:
        print(f"  image aligned to 512-byte sectors: OK")

    print()
    make_iso(os.path.join(BUILD, "os-image.img"),
             os.path.join(BUILD, "LunarOS.iso"))

if __name__ == "__main__":
    build()