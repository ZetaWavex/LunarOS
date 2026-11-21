#include "graphics.h"
#include "asc48_lunaros.h"
#include "logo_data.h"

#define ARC_STEP      6
#define ARC_DELAY_US  15000
#define RING_BOX_MAX 128
#define RING_SCALE  55
#define TEXT_SCALE  65

#define LOAD_FRAMES  190
#define PWD_MAX       24
#define PWD_LBA       256

static inline void outb(u16 port, u8 val) {
    __asm__ __volatile__("outb %0, %1" :: "a"(val), "Nd"(port));
}

static inline u8 inb(u16 port) {
    u8 r;
    __asm__ __volatile__("inb %1, %0" : "=a"(r) : "Nd"(port));
    return r;
}

static inline u16 inw(u16 port) {
    u16 r;
    __asm__ __volatile__("inw %1, %0" : "=a"(r) : "Nd"(port));
    return r;
}

static inline void outw(u16 port, u16 val) {
    __asm__ __volatile__("outw %0, %1" :: "a"(val), "Nd"(port));
}

static void serial_putc(char c) {
    while (!(inb(0x3FD) & 0x20)) { }
    outb(0x3F8, (u8)c);
}

static u16 pit2_read(void) {
    outb(0x43, 0x80);
    u16 v = inb(0x42);
    v |= (u16)inb(0x42) << 8;
    return v;
}

static void delay_us(u32 us) {
    u8 gate = inb(0x61);
    outb(0x61, (u8)(gate | 0x01));

    while (us > 0) {
        u32 chunk = us > 50000u ? 50000u : us;
        us -= chunk;

        u32 ticks = (chunk * 1193u + 500u) / 1000u;
        if (ticks < 2) ticks = 2;
        if (ticks > 0xFFFEu) ticks = 0xFFFEu;

        outb(0x43, 0xB0);
        outb(0x42, (u8)(ticks & 0xFF));
        outb(0x42, (u8)((ticks >> 8) & 0xFF));

        u32 guard = 0x400000u;
        while (guard-- > 0) {
            u16 now = pit2_read();
            if (now == 0) break;
        }
    }

    outb(0x61, gate);
}

static void serial_puts(const char *s) {
    while (*s) serial_putc(*s++);
}

static void serial_putnum(u32 v) {
    char buf[12];
    int i = 0;
    if (v == 0) { serial_putc('0'); return; }
    while (v && i < 12) { buf[i++] = (char)('0' + (v % 10)); v /= 10; }
    while (i > 0) serial_putc(buf[--i]);
}

static u8 *fb;
static u32 fb_pitch;
static u32 fb_bpp;
static u32 scr_w;
static u32 scr_h;
static int ui_kx = 100;
static int ui_ky = 100;
static int ui_k = 100;

static int scx(int v) { return v * ui_k / 100; }
static int scy(int v) { return v * ui_k / 100; }

static u32 pack(u8 r, u8 g, u8 b) {
    if (fb_bpp == 32) return ((u32)r << 16) | ((u32)g << 8) | (u32)b;
    if (fb_bpp == 24) return ((u32)r << 16) | ((u32)g << 8) | (u32)b;
    return (u32)((u16)((r & 0xF8) << 8) | (u16)((g & 0xFC) << 3) | (b >> 3));
}

static void px(int x, int y, u32 c) {
    if (x < 0 || y < 0 || (u32)x >= scr_w || (u32)y >= scr_h) return;
    u32 off = (u32)y * fb_pitch + (u32)x * (fb_bpp / 8);
    if (fb_bpp == 32) {
        *(u32 *)(fb + off) = c;
    } else if (fb_bpp == 24) {
        fb[off] = (u8)(c & 0xFF);
        fb[off + 1] = (u8)((c >> 8) & 0xFF);
        fb[off + 2] = (u8)((c >> 16) & 0xFF);
    } else {
        *(u16 *)(fb + off) = (u16)c;
    }
}

static u32 get_px(int x, int y) {
    if (x < 0 || y < 0 || (u32)x >= scr_w || (u32)y >= scr_h) return 0;
    u32 off = (u32)y * fb_pitch + (u32)x * (fb_bpp / 8);
    if (fb_bpp == 32) return *(u32 *)(fb + off);
    if (fb_bpp == 24)
        return (u32)fb[off] | ((u32)fb[off + 1] << 8) | ((u32)fb[off + 2] << 16);
    return (u32)(*(u16 *)(fb + off));
}

static void bg_rgb(int y, u8 *r, u8 *g, u8 *b) {
    if (y < 0) y = 0;
    if ((u32)y >= scr_h) y = (int)scr_h - 1;
    u32 den = scr_h ? scr_h : 1;
    u32 t = (u32)y * 1000u / den;
    *r = (u8)((10u * (1000u - t)) / 1000u);
    *g = (u8)((16u * (1000u - t)) / 1000u);
    *b = (u8)((38u * (1000u - t)) / 1000u);
}

static u32 bg_at(int y) {
    u8 r, g, b;
    bg_rgb(y, &r, &g, &b);
    return pack(r, g, b);
}

static void cursor_redraw(void);

static void fill_bg_rect(int x, int y, int w, int h) {
    for (int j = 0; j < h; j++) {
        u32 c = bg_at(y + j);
        for (int i = 0; i < w; i++) px(x + i, y + j, c);
    }
}

static void draw_background(void) {
    for (u32 y = 0; y < scr_h; y++) {
        u32 c = bg_at((int)y);
        for (u32 x = 0; x < scr_w; x++)
            px((int)x, (int)y, c);
    }
}

static void draw_logo(int cx, int cy, int w, int h) {
    int x0 = cx - w / 2;
    int y0 = cy - h / 2;
    if (w < 1) w = 1;
    if (h < 1) h = 1;
    for (int j = 0; j < h; j++) {
        int sy = (int)((long)j * LOGO_H / h);
        for (int i = 0; i < w; i++) {
            int sx = (int)((long)i * LOGO_W / w);
            u8 idx = logo_idx[sy * LOGO_W + sx];
            u8 a = logo_pal[idx * 4 + 3];
            if (a == 0) continue;
            u8 r = logo_pal[idx * 4 + 0];
            u8 g = logo_pal[idx * 4 + 1];
            u8 b = logo_pal[idx * 4 + 2];
            if (a != 255) {
                u8 br, bgc, bb;
                bg_rgb(y0 + j, &br, &bgc, &bb);
                r = (u8)(((u32)r * a + (u32)br * (255 - a)) / 255);
                g = (u8)(((u32)g * a + (u32)bgc * (255 - a)) / 255);
                b = (u8)(((u32)b * a + (u32)bb * (255 - a)) / 255);
            }
            px(x0 + i, y0 + j, pack(r, g, b));
        }
    }
}

static int text_track(int pctx) {
    int t = (6 * pctx + 50) / 100;
    return t < 2 ? 2 : t;
}

static int text_width(int pctx) {
    int track = text_track(pctx);
    int total = 0;
    for (int i = 0; i < ASC48_TEXT_COUNT; i++)
        total += (asc48_text_table[i].w * pctx + 50) / 100 + track;
    total -= track;
    return total;
}

static int text_height(int pcty) {
    int h = (ASC48_CELL * pcty + 50) / 100;
    return h < 1 ? 1 : h;
}

static void draw_text_at(int y, int pctx, int pcty) {
    int track = text_track(pctx);
    int total = text_width(pctx);
    int x = (int)scr_w / 2 - total / 2;
    int h = text_height(pcty);

    u32 fg = pack(235, 235, 235);
    for (int i = 0; i < ASC48_TEXT_COUNT; i++) {
        const asc48_glyph_t *g = &asc48_text_table[i];
        const u8 *bits = asc48_text_bits + (u32)i * ASC48_GLYPH_BYTES;
        int gw = (g->w * pctx + 50) / 100;
        if (gw < 1) gw = 1;
        for (int row = 0; row < h; row++) {
            int sy = row * ASC48_CELL / h;
            for (int col = 0; col < gw; col++) {
                int sx = g->x0 + col * g->w / gw;
                u8 b = bits[sy * ASC48_ROW_BYTES + (sx >> 3)];
                if (b & (0x80 >> (sx & 7)))
                    px(x + col, y + row, fg);
            }
        }
        x += gw + track;
    }
}

static void draw_ring_box(u32 *buf, int bw, int bh, int bcx, int bcy,
                          int base_y, int rx, int ry, int th, int phase, u32 color) {
    int stride = bw;
    for (int j = 0; j < bh; j++) {
        u32 c = bg_at(base_y + j);
        for (int i = 0; i < bw; i++)
            buf[j * stride + i] = c;
    }
    gfx_set_target(buf, stride, bw, bh);
    gfx_draw_ellipse_arc(bcx, bcy, rx, ry, phase, phase + 70, color, th);
    gfx_draw_ellipse_arc(bcx, bcy, rx, ry, phase + 120, phase + 190, color, th);
    gfx_draw_ellipse_arc(bcx, bcy, rx, ry, phase + 240, phase + 310, color, th);
    gfx_reset_target();
}

static int ata_read_sector(u32 lba, u8 *out) {
    u32 guard;

    outb(0x1F6, (u8)(0xE0 | ((lba >> 24) & 0x0F)));
    outb(0x1F2, 1);
    outb(0x1F3, (u8)(lba & 0xFF));
    outb(0x1F4, (u8)((lba >> 8) & 0xFF));
    outb(0x1F5, (u8)((lba >> 16) & 0xFF));
    outb(0x1F7, 0x20);

    guard = 0x100000u;
    while (guard-- > 0) {
        u8 st = inb(0x1F7);
        if (!(st & 0x80)) break;
    }
    if (guard == 0xFFFFFFFFu) return 0;

    guard = 0x100000u;
    while (guard-- > 0) {
        u8 st = inb(0x1F7);
        if (st & 0x01) return 0;
        if (st & 0x08) break;
    }
    if (!(inb(0x1F7) & 0x08)) return 0;

    for (int i = 0; i < 256; i++) {
        u16 w = inw(0x1F0);
        out[i * 2 + 0] = (u8)(w & 0xFF);
        out[i * 2 + 1] = (u8)(w >> 8);
    }
    return 1;
}

static u32 sha_k[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
};

static u32 ror32(u32 x, int n) {
    return (x >> n) | (x << (32 - n));
}

static void sha256_block(u32 *h, const u8 *p) {
    u32 w[64];
    u32 a, b, c, d, e, f, g, hh;

    for (int i = 0; i < 16; i++)
        w[i] = ((u32)p[i * 4] << 24) | ((u32)p[i * 4 + 1] << 16) |
               ((u32)p[i * 4 + 2] << 8) | (u32)p[i * 4 + 3];
    for (int i = 16; i < 64; i++) {
        u32 s0 = ror32(w[i - 15], 7) ^ ror32(w[i - 15], 18) ^ (w[i - 15] >> 3);
        u32 s1 = ror32(w[i - 2], 17) ^ ror32(w[i - 2], 19) ^ (w[i - 2] >> 10);
        w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }

    a = h[0]; b = h[1]; c = h[2]; d = h[3];
    e = h[4]; f = h[5]; g = h[6]; hh = h[7];

    for (int i = 0; i < 64; i++) {
        u32 s1 = ror32(e, 6) ^ ror32(e, 11) ^ ror32(e, 25);
        u32 ch = (e & f) ^ ((~e) & g);
        u32 t1 = hh + s1 + ch + sha_k[i] + w[i];
        u32 s0 = ror32(a, 2) ^ ror32(a, 13) ^ ror32(a, 22);
        u32 mj = (a & b) ^ (a & c) ^ (b & c);
        u32 t2 = s0 + mj;
        hh = g; g = f; f = e; e = d + t1;
        d = c; c = b; b = a; a = t1 + t2;
    }

    h[0] += a; h[1] += b; h[2] += c; h[3] += d;
    h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
}

static u32 str_len(const char *s) {
    u32 n = 0;
    while (s[n]) n++;
    return n;
}

static void sha256_hex(const u8 *data, u32 len, char *out) {
    u32 h[8] = {
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    };
    u8 blk[64];
    u32 total = len;
    u32 off = 0;

    while (len >= 64) {
        sha256_block(h, data + off);
        off += 64;
        len -= 64;
    }

    for (int j = 0; j < 64; j++) blk[j] = 0;
    for (u32 j = 0; j < len; j++) blk[j] = data[off + j];
    blk[len] = 0x80;

    if (len >= 56) {
        sha256_block(h, blk);
        for (int j = 0; j < 64; j++) blk[j] = 0;
    }

    u32 bits = total * 8u;
    blk[63] = (u8)(bits & 0xFF);
    blk[62] = (u8)((bits >> 8) & 0xFF);
    blk[61] = (u8)((bits >> 16) & 0xFF);
    blk[60] = (u8)((bits >> 24) & 0xFF);
    sha256_block(h, blk);

    for (int j = 0; j < 32; j++) {
        u8 v = (u8)((h[j >> 2] >> (24 - (j & 3) * 8)) & 0xFF);
        out[j * 2 + 0] = "0123456789abcdef"[(v >> 4) & 0x0F];
        out[j * 2 + 1] = "0123456789abcdef"[v & 0x0F];
    }
    out[64] = 0;
}

static char pwd_stored[65];
static int  pwd_loaded = 0;

static void load_password(void) {
    static u8 sec[512];
    pwd_loaded = 0;
    if (!ata_read_sector(PWD_LBA, sec)) {
        serial_puts("[PWD] read failed\n");
        return;
    }

    int n = 0;
    for (int i = 0; i < 64; i++) {
        char c = (char)sec[i];
        if (c >= '0' && c <= '9') { pwd_stored[n++] = c; continue; }
        if (c >= 'a' && c <= 'f') { pwd_stored[n++] = c; continue; }
        if (c >= 'A' && c <= 'F') { pwd_stored[n++] = (char)(c - 'A' + 'a'); continue; }
        n = 0;
        break;
    }
    pwd_stored[n] = 0;
    pwd_loaded = (n == 64);
    serial_puts("[PWD] digest=");
    serial_puts(pwd_stored);
    serial_puts(pwd_loaded ? " (ok)\n" : " (bad)\n");
}

static int password_match(const char *pw) {
    char hex[65];
    if (!pwd_loaded) return 0;
    sha256_hex((const u8 *)pw, (u32)str_len(pw), hex);
    for (int i = 0; i < 64; i++)
        if (hex[i] != pwd_stored[i]) return 0;
    return 1;
}

static u8 kbd_status(void) { return inb(0x64); }

static void kbd_wait_write(void) {
    u32 guard = 0x10000u;
    while (guard-- > 0) {
        if (!(inb(0x64) & 0x02)) return;
    }
}

static void kbd_wait_read(void) {
    u32 guard = 0x10000u;
    while (guard-- > 0) {
        if (inb(0x64) & 0x01) return;
    }
}

static void kbd_cmd(u8 c) {
    kbd_wait_write();
    outb(0x64, c);
}

static void mouse_write(u8 v) {
    kbd_cmd(0xD4);
    kbd_wait_write();
    outb(0x60, v);
}

static void mouse_init(void) {
    kbd_cmd(0xA8);
    kbd_cmd(0x20);
    kbd_wait_read();
    u8 cfg = inb(0x60);
    cfg = (u8)((cfg | 0x02) & ~0x20);
    kbd_cmd(0x60);
    kbd_wait_write();
    outb(0x60, cfg);

    mouse_write(0xF6);
    kbd_wait_read();
    inb(0x60);

    mouse_write(0xF4);
    kbd_wait_read();
    inb(0x60);

    while (inb(0x64) & 0x01) inb(0x60);
}

static int  mouse_cycle = 0;
static u8   mouse_buf[3];
static int  mouse_x = 0;
static int  mouse_y = 0;
static int  mouse_moved = 0;
static int  mouse_buttons = 0;
static int  mouse_press = 0;

static void mouse_poll(void) {
    u32 guard = 64;
    while (guard-- > 0) {
        u8 st = inb(0x64);
        if (!(st & 0x01)) break;
        if (!(st & 0x20)) break;

        u8 data = inb(0x60);
        if (mouse_cycle == 0 && !(data & 0x08)) continue;

        mouse_buf[mouse_cycle++] = data;
        if (mouse_cycle < 3) continue;
        mouse_cycle = 0;

        int dx = (int)mouse_buf[1] - ((mouse_buf[0] & 0x10) ? 256 : 0);
        int dy = (int)mouse_buf[2] - ((mouse_buf[0] & 0x20) ? 256 : 0);

        if (dx || dy) {
            mouse_x += dx;
            mouse_y -= dy;
            if (mouse_x < 0) mouse_x = 0;
            if (mouse_y < 0) mouse_y = 0;
            if (mouse_x > (int)scr_w - 1) mouse_x = (int)scr_w - 1;
            if (mouse_y > (int)scr_h - 1) mouse_y = (int)scr_h - 1;
            mouse_moved = 1;
        }

        int btns = mouse_buf[0] & 0x07;
        if ((btns & 0x01) && !(mouse_buttons & 0x01)) {
            mouse_moved = 1;
            mouse_press = 1;
        }
        mouse_buttons = btns;
    }
}

static int kbd_e0 = 0;

static char kbd_poll(void) {
    if (!(kbd_status() & 0x01)) return 0;
    if (kbd_status() & 0x20) return 0;
    u8 sc = inb(0x60);

    if (sc == 0xE0) { kbd_e0 = 1; return 0; }
    if (sc == 0xE1) { kbd_e0 = 2; return 0; }

    int ext = kbd_e0;
    kbd_e0 = 0;

    if (sc & 0x80) return 0;

    if (!ext) {
        if (sc >= 0x02 && sc <= 0x0B) {
            static const char digits[10] = {'1','2','3','4','5','6','7','8','9','0'};
            return digits[sc - 0x02];
        }
    }

    if (!ext && sc >= 0x47 && sc <= 0x52) {
        static const char keypad[12] = {'7','8','9',0,'4','5','6',0,'1','2','3','0'};
        char c = keypad[sc - 0x47];
        if (c) return c;
    }

    if (sc == 0x1C) return '\n';
    if (sc == 0x0E) return '\b';
    return 0;
}

static void draw_char(int x, int y, char c, int sx, int sy, u32 fg) {
    int w = 8 * sx;
    int h = 16 * sy;
    for (int row = 0; row < h; row++) {
        u8 bits = gfx_get_glyph((u8)c, row / sy);
        for (int col = 0; col < w; col++) {
            if (bits & (0x80 >> (col / sx)))
                px(x + col, y + row, fg);
        }
    }
}

static void draw_string(int x, int y, const char *s, int sx, int sy, u32 fg) {
    while (*s) {
        draw_char(x, y, *s, sx, sy, fg);
        x += 8 * sx + sx;
        s++;
    }
}

static int string_width(const char *s, int sx) {
    int n = 0;
    while (s[n]) n++;
    if (n == 0) return 0;
    return n * (8 * sx + sx) - sx;
}

static void draw_string_center(int y, const char *s, int sx, int sy, u32 fg) {
    int w = string_width(s, sx);
    draw_string((int)scr_w / 2 - w / 2, y, s, sx, sy, fg);
}

static int in_round(int i, int j, int w, int h, int r) {
    if (r < 1) return 1;
    if (r * 2 > w) r = w / 2;
    if (r * 2 > h) r = h / 2;
    if (r < 1) return 1;
    int a = 0, b = 0;
    if (i < r) a = 2 * i + 1 - 2 * r;
    else if (i >= w - r) a = 2 * (i - (w - r)) + 1;
    if (j < r) b = 2 * j + 1 - 2 * r;
    else if (j >= h - r) b = 2 * (j - (h - r)) + 1;
    return a * a + b * b <= 4 * r * r;
}

static void fill_round_rect(int x, int y, int w, int h, int r, u32 c) {
    for (int j = 0; j < h; j++)
        for (int i = 0; i < w; i++)
            if (in_round(i, j, w, h, r))
                px(x + i, y + j, c);
}

static void draw_round_border(int x, int y, int w, int h, int t, int r, u32 c) {
    if (t < 1) t = 1;
    int iw = w - 2 * t;
    int ih = h - 2 * t;
    int ir = r - t;
    if (ir < 0) ir = 0;
    for (int j = 0; j < h; j++) {
        for (int i = 0; i < w; i++) {
            if (!in_round(i, j, w, h, r)) continue;
            if (iw > 0 && ih > 0 &&
                in_round(i - t, j - t, iw, ih, ir)) continue;
            px(x + i, y + j, c);
        }
    }
}

#include "cursor_data.h"

#define CURSOR_ARROW 0
#define CURSOR_BEAM  1

typedef struct {
    const unsigned char *px;
    int w, h;
    int hotx, hoty;
    int scale;
} cursor_img_t;

static const cursor_img_t cursor_imgs[2] = {
    { cursor_arrow_rgba, CURSOR_ARROW_W, CURSOR_ARROW_H,
      CURSOR_ARROW_HOTX, CURSOR_ARROW_HOTY, 64 },
    { cursor_beam_rgba, CURSOR_BEAM_W, CURSOR_BEAM_H,
      CURSOR_BEAM_HOTX, CURSOR_BEAM_HOTY, 20 },
};

#define UI_K_MAX 400

#define CUR_BUF_W (CURSOR_MAX_W * UI_K_MAX / 100 + 2)
#define CUR_BUF_H (CURSOR_MAX_H * UI_K_MAX / 100 + 2)

static int cur_shape = CURSOR_ARROW;
static int cur_drawn = 0;
static int cur_px = 0;
static int cur_py = 0;
static int cur_w = 0;
static int cur_h = 0;
static u32 cur_save[CUR_BUF_W * CUR_BUF_H];

static u32 blend(u32 dst, u8 r, u8 g, u8 b, u8 a) {
    if (a == 0) return dst;
    if (a == 255) return pack(r, g, b);

    u8 dr, dg, db;
    if (fb_bpp == 32) {
        dr = (u8)((dst >> 16) & 0xFF);
        dg = (u8)((dst >> 8) & 0xFF);
        db = (u8)(dst & 0xFF);
    } else if (fb_bpp == 24) {
        dr = (u8)((dst >> 16) & 0xFF);
        dg = (u8)((dst >> 8) & 0xFF);
        db = (u8)(dst & 0xFF);
    } else {
        dr = (u8)(((dst >> 11) & 0x1F) << 3);
        dg = (u8)(((dst >> 5) & 0x3F) << 2);
        db = (u8)((dst & 0x1F) << 3);
    }

    u8 nr = (u8)((r * a + dr * (255 - a)) / 255);
    u8 ng = (u8)((g * a + dg * (255 - a)) / 255);
    u8 nb = (u8)((b * a + db * (255 - a)) / 255);
    return pack(nr, ng, nb);
}

static void cursor_erase(void) {
    if (!cur_drawn) return;
    for (int j = 0; j < cur_h; j++)
        for (int i = 0; i < cur_w; i++)
            px(cur_px + i, cur_py + j, cur_save[j * cur_w + i]);
    cur_drawn = 0;
}

static void cursor_draw(void) {
    const cursor_img_t *c = &cursor_imgs[cur_shape];

    cur_w = (c->w * ui_k * c->scale) / 10000;
    cur_h = (c->h * ui_k * c->scale) / 10000;
    if (cur_w < 1) cur_w = 1;
    if (cur_h < 1) cur_h = 1;
    if (cur_w > CUR_BUF_W) cur_w = CUR_BUF_W;
    if (cur_h > CUR_BUF_H) cur_h = CUR_BUF_H;

    cur_px = mouse_x - (c->hotx * ui_k * c->scale) / 10000;
    cur_py = mouse_y - (c->hoty * ui_k * c->scale) / 10000;

    for (int j = 0; j < cur_h; j++) {
        int sy = j * c->h / cur_h;
        for (int i = 0; i < cur_w; i++) {
            int x = cur_px + i;
            int y = cur_py + j;
            if (x < 0 || y < 0 || (u32)x >= scr_w || (u32)y >= scr_h) continue;

            u32 dst = get_px(x, y);
            cur_save[j * cur_w + i] = dst;

            int sx = i * c->w / cur_w;
            int si = (sy * c->w + sx) * 4;
            u8 r = c->px[si];
            u8 g = c->px[si + 1];
            u8 b = c->px[si + 2];
            u8 a = c->px[si + 3];
            if (a) px(x, y, blend(dst, r, g, b, a));
        }
    }
    cur_drawn = 1;
}

static void cursor_update(void) {
    if (!mouse_moved) return;
    mouse_moved = 0;
    cursor_erase();
    cursor_draw();
}

static void cursor_redraw(void) {
    cursor_erase();
    cursor_draw();
}

static void cursor_set(int shape) {
    if (shape == cur_shape) return;
    int was_drawn = cur_drawn;
    if (was_drawn) cursor_erase();
    cur_shape = shape;
    if (was_drawn) cursor_draw();
}

static char pwd_input[PWD_MAX + 1];
static int  pwd_len = 0;

static int box_w = 320;
static int box_h = 40;
static int box_x = 240;
static int box_y = 360;

static int login_focus = 1;
static int caret_on = 1;
static int caret_tick = 0;

static int box_radius(void) {
    int r = ui_k * 10 / 100;
    if (r < 4) r = 4;
    if (r > box_h / 2) r = box_h / 2;
    return r;
}

static void dot_layout(int n, int *pr, int *pstep) {
    int r = scx(5);
    if (r < 3) r = 3;
    int pad = box_radius();
    int avail = box_w - pad * 2;
    int step = r * 4;
    if (n > 1) {
        if ((long)step * (n - 1) + 2 * r > avail) {
            step = r * 2;
            if ((long)step * (n - 1) + 2 * r > avail) {
                r = avail / (2 * n);
                if (r < 2) r = 2;
                step = r * 2;
            }
        }
    }
    *pr = r;
    *pstep = step;
}

static void draw_login_box(void) {
    u32 box_bg   = pack(18, 24, 42);
    u32 box_line = pack(64, 84, 128);
    u32 white    = pack(240, 240, 240);

    int box_r = box_radius();

    fill_round_rect(box_x, box_y, box_w, box_h, box_r, box_bg);
    draw_round_border(box_x, box_y, box_w, box_h, 2, box_r, box_line);

    int dy = box_y + box_h / 2;
    int dx = box_x + box_r;

    int r, step;
    dot_layout(pwd_len, &r, &step);

    for (int i = 0; i < pwd_len; i++) {
        for (int j = -r; j <= r; j++)
            for (int ii = -r; ii <= r; ii++)
                if ((long)ii * ii + (long)j * j <= (long)r * r)
                    px(dx + ii, dy + j, white);
        dx += step;
    }

    if (login_focus && caret_on) {
        int ch = scy(18);
        int cw = scx(2);
        if (cw < 1) cw = 1;
        if (cw > 3) cw = 3;
        for (int j = -ch / 2; j <= ch / 2; j++)
            for (int i = 0; i < cw; i++)
                px(dx + i, dy + j, white);
    }
}

static void draw_login_static(void) {
    int cx = (int)scr_w / 2;

    draw_background();

    int logo_w = scx(88);
    int logo_h = scy(88);
    if (logo_w < 32) logo_w = 32;
    if (logo_h < 32) logo_h = 32;
    int logo_cy = (int)scr_h * 34 / 100;
    draw_logo(cx, logo_cy, logo_w, logo_h);

    int tpx = ui_k * 48 / 100;
    if (tpx < 16) tpx = 16;
    while (tpx > 16 && text_width(tpx) > (int)scr_w - 40)
        tpx--;
    int tpy = ui_k * 48 / 100;
    if (tpy < 16) tpy = 16;
    int text_y = logo_cy + logo_h / 2 + scy(22);
    draw_text_at(text_y, tpx, tpy);

    int sc = ui_k * 3 / 200;
    if (sc < 1) sc = 1;
    int scy_f = ui_k * 3 / 200;
    if (scy_f < 1) scy_f = 1;
    u32 gray = pack(150, 158, 175);
    draw_string_center(text_y + text_height(tpy) + scy(26),
                       "Enter your password", sc, scy_f, gray);

    draw_login_box();
}

static void draw_login_message(const char *msg, int bad) {
    int sc = ui_k * 3 / 200;
    if (sc < 1) sc = 1;
    int sy = ui_k * 3 / 200;
    if (sy < 1) sy = 1;
    u32 color = bad ? pack(230, 90, 90) : pack(120, 220, 150);
    int h = 16 * sy;
    int y = box_y + box_h + scy(18);
    fill_bg_rect(0, y - 2, (int)scr_w, h + 4);
    int w = string_width(msg, sc);
    draw_string((int)scr_w / 2 - w / 2, y, msg, sc, sy, color);
}

static void draw_welcome(void) {
    int cx = (int)scr_w / 2;
    draw_background();

    int logo_w = scx(104);
    int logo_h = scy(104);
    if (logo_w < 32) logo_w = 32;
    if (logo_h < 32) logo_h = 32;
    int logo_cy = (int)scr_h / 2 - scy(60);
    draw_logo(cx, logo_cy, logo_w, logo_h);

    int sc = ui_k * 4 / 200;
    if (sc < 1) sc = 1;
    int sy = ui_k * 4 / 200;
    if (sy < 1) sy = 1;
    draw_string_center((int)scr_h / 2 + scy(40),
                       "Welcome to LunarOS", sc, sy, pack(240, 240, 240));
}

static void run_boot_animation(void) {
    int cx = (int)scr_w / 2;

    draw_background();

    int logo_w = 200;
    int logo_h = 200;

    int tpct = ui_k * TEXT_SCALE / 100;
    if (tpct < 20) tpct = 20;
    while (tpct > 20 && text_width(tpct) > (int)scr_w - 40)
        tpct--;

    int rx = (34 * ui_k * RING_SCALE + 5000) / 10000;
    int ry = (34 * ui_k * RING_SCALE + 5000) / 10000;
    int th = (5 * ui_k * RING_SCALE + 5000) / 10000;
    if (rx < 8) rx = 8;
    if (ry < 8) ry = 8;
    if (th < 2) th = 2;

    int gap1 = scy(30);
    int gap2 = scy(40);
    if (gap1 < 8) gap1 = 8;
    if (gap2 < 10) gap2 = 10;

    int text_h = text_height(ui_k * TEXT_SCALE / 100);

    int block_h = logo_h + gap1 + text_h + gap2 + (ry + th) * 2;
    int top = ((int)scr_h - block_h) / 2;
    if (top < 0) top = 0;

    int logo_cy = top + logo_h / 2;
    int text_y  = top + logo_h + gap1;
    int cy      = text_y + text_h + gap2 + ry + th;

    draw_logo(cx, logo_cy, logo_w, logo_h);
    draw_text_at(text_y, tpct, ui_k * TEXT_SCALE / 100);
    serial_puts("[KERNEL] boot screen ready\n");

    int phase = 0;
    u32 white = pack(255, 255, 255);

    int box_w = (rx + th + 3) * 2;
    int box_h = (ry + th + 3) * 2;
    if (box_w > RING_BOX_MAX) box_w = RING_BOX_MAX;
    if (box_h > RING_BOX_MAX) box_h = RING_BOX_MAX;
    int box_x = cx - box_w / 2;
    int box_y = cy - box_h / 2;
    static u32 ring_buf[RING_BOX_MAX * RING_BOX_MAX];
    int bcx = box_w / 2;
    int bcy = box_h / 2;

    for (int f = 0; f < LOAD_FRAMES; f++) {
        mouse_poll();
        mouse_moved = 0;

        draw_ring_box(ring_buf, box_w, box_h, bcx, bcy, box_y, rx, ry, th, phase, white);
        gfx_blit_buffer(ring_buf, box_w, box_x, box_y, box_w, box_h);
        phase = (phase + ARC_STEP) % 360;

        delay_us(ARC_DELAY_US);
    }
}

static void login_screen(void) {
    int sc_msg_x = ui_k * 3 / 200;
    int sc_msg_y = ui_k * 3 / 200;
    if (sc_msg_x < 1) sc_msg_x = 1;
    if (sc_msg_y < 1) sc_msg_y = 1;

    box_w = scx(232);
    box_h = scy(32);
    if (box_w < 160) box_w = 160;
    if (box_h < 24) box_h = 24;
    box_x = ((int)scr_w - box_w) / 2;
    box_y = (int)scr_h * 60 / 100;

    pwd_len = 0;
    pwd_input[0] = 0;
    login_focus = 1;
    caret_on = 1;
    caret_tick = 0;
    mouse_press = 0;

    draw_login_static();
    cursor_redraw();

    int msg_y = box_y + box_h + scy(18);
    int msg_h = 16 * sc_msg_y + 4;
    fill_bg_rect(0, msg_y - 2, (int)scr_w, msg_h);
    cursor_redraw();

    while (1) {
        delay_us(1000);
        mouse_poll();
        int in_box = (mouse_x >= box_x && mouse_x < box_x + box_w &&
                      mouse_y >= box_y && mouse_y < box_y + box_h);

        if (mouse_press) {
            mouse_press = 0;
            int want = in_box ? 1 : 0;
            if (want != login_focus || (want && !caret_on)) {
                login_focus = want;
                caret_tick = 0;
                caret_on = 1;
                cursor_erase();
                draw_login_box();
                cursor_redraw();
            }
        }

        cursor_set(in_box ? CURSOR_BEAM : CURSOR_ARROW);
        cursor_update();

        caret_tick++;
        if (caret_tick >= 500) {
            caret_tick = 0;
            caret_on = !caret_on;
            if (login_focus) {
                cursor_erase();
                draw_login_box();
                cursor_redraw();
            }
        }

        char ch = kbd_poll();
        if (!ch) continue;
        if (!login_focus) continue;

        caret_tick = 0;
        caret_on = 1;

        if (ch == '\n') {
            if (pwd_len == 0) continue;
            pwd_input[pwd_len] = 0;
            if (password_match(pwd_input)) {
                serial_puts("[LOGIN] success\n");
                return;
            }
            serial_puts("[LOGIN] failed\n");
            pwd_len = 0;
            pwd_input[0] = 0;
            cursor_erase();
            draw_login_static();
            draw_login_message("Wrong password, try again", 1);
            cursor_redraw();
            continue;
        }

        if (ch == '\b') {
            if (pwd_len > 0) {
                pwd_len--;
                pwd_input[pwd_len] = 0;
                cursor_erase();
                draw_login_box();
                cursor_redraw();
            }
            continue;
        }

        if (pwd_len < PWD_MAX) {
            if (ch < '0' || ch > '9') continue;
            pwd_input[pwd_len++] = ch;
            pwd_input[pwd_len] = 0;
            cursor_erase();
            draw_login_box();
            cursor_redraw();
        }
    }
}

void kernel_main(u32 lfb, u32 width, u32 height, u32 bpp, u32 pitch) {
    gfx_info_t info;

    info.width  = width;
    info.height = height;
    info.bpp    = bpp;
    info.pitch  = pitch;
    info.lfb    = lfb;
    gfx_init(&info);

    fb = (u8 *)(u32)lfb;
    fb_pitch = pitch;
    fb_bpp = bpp;
    scr_w = width;
    scr_h = height;

    ui_kx = (int)(scr_w * 100u / 800u);
    ui_ky = (int)(scr_h * 100u / 600u);
    if (ui_kx < 50) ui_kx = 50;
    if (ui_ky < 50) ui_ky = 50;
    if (ui_kx > UI_K_MAX) ui_kx = UI_K_MAX;
    if (ui_ky > UI_K_MAX) ui_ky = UI_K_MAX;

    ui_k = ui_kx < ui_ky ? ui_kx : ui_ky;

    serial_puts("[KERNEL] gfx ready ");
    serial_putnum(scr_w);
    serial_putc('x');
    serial_putnum(scr_h);
    serial_putc(' ');
    serial_putnum(fb_bpp);
    serial_puts("bpp\n");

    load_password();

    mouse_x = (int)scr_w / 2;
    mouse_y = (int)scr_h / 2;
    mouse_init();

    run_boot_animation();
    serial_puts("[KERNEL] loading finished, entering login\n");

    login_screen();

    cursor_set(CURSOR_ARROW);
    cursor_erase();
    draw_welcome();
    cursor_redraw();
    serial_puts("[KERNEL] logged in\n");

    while (1) {
        kbd_poll();
        mouse_poll();
        cursor_update();
        delay_us(1000);
    }
}