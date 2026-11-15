import re

SRC = r"D:\NewX\OS\Try 5\HZKX\asc48.bin"
MAP = r"D:\NewX\OS\Try 5\HZKX\asc48_map.h"
OUT = r"D:\NewX\OS\Try 5\src\asc48_lunaros.h"

font = open(SRC, "rb").read()
txt = open(MAP, encoding="utf-8").read()
body = txt.split("asc48_lookup[128] = {")[1].split("};")[0]
lookup = [int(x) for x in re.findall(r"-?\d+", body)]

chars = "LunarOS"
glyphs = []
meta = []
for ch in chars:
    off = lookup[ord(ch)] * 288
    g = font[off:off + 288]
    glyphs.append(g)
    xs = []
    for r in range(48):
        for i in range(6):
            b = g[r * 6 + i]
            for k in range(8):
                if b & (0x80 >> k):
                    xs.append(i * 8 + k)
    x0 = min(xs)
    w = max(xs) - x0 + 1
    meta.append((ch, x0, w))

lines = []
lines.append("#ifndef ASC48_LUNAROS_H")
lines.append("#define ASC48_LUNAROS_H")
lines.append("")
lines.append('#include "graphics.h"')
lines.append("")
lines.append("#define ASC48_CELL        48")
lines.append("#define ASC48_ROW_BYTES   6")
lines.append("#define ASC48_GLYPH_BYTES  288")
lines.append("#define ASC48_TEXT_COUNT   %d" % len(chars))
lines.append("")
lines.append("typedef struct {")
lines.append("    u8 code;")
lines.append("    u8 x0;")
lines.append("    u8 w;")
lines.append("} asc48_glyph_t;")
lines.append("")
lines.append("static const u8 asc48_text_bits[] = {")
for g in glyphs:
    lines.append("    ")
    for row in range(0, 288, 16):
        lines.append("    " + ", ".join("0x%02X" % b for b in g[row:row + 16]) + ",")
lines.append("};")
lines.append("")
lines.append("static const asc48_glyph_t asc48_text_table[ASC48_TEXT_COUNT] = {")
for ch, x0, w in meta:
    lines.append("    {'%s', %d, %d}," % (ch, x0, w))
lines.append("};")
lines.append("")
lines.append("#endif")

open(OUT, "w", encoding="ascii").write("\n".join(lines) + "\n")
print("glyphs:", meta)
print("total bytes:", len(glyphs) * 288)