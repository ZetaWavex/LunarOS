#include "graphics.h"
#include "asc48_lunaros.h"
#include "logo_data.h"

extern void delay_asm(u32 n);

#define ARC_STEP      6
#define ARC_DELAY_US  25000
#define RING_BOX_MAX 128
#define RING_SCALE  55
#define TEXT_SCALE  65

static inline void outb(u16 port, u8 val) {
    __asm__ __volatile__("outb %0, %1" :: "a"(val), "Nd"(port));
}

static inline u8 inb(u16 port) {
    u8 r;
    __asm__ __volatile__("inb %1, %0" : "=a"(r) : "Nd"(port));
    return r;
}

static void serial_putc(char c) {
    while (!(inb(0x3FD) & 0x20)) { }
    outb(0x3F8, (u8)c);
}

static inline void io_wait(void) {
    outb(0x80, 0);
}

static u16 pit_read(void) {
    outb(0x43, 0x80);
    u16 v = inb(0x40);
    v |= (u16)inb(0x40) << 8;
    return v;
}

static void delay_us(u32 us) {
    u32 chunks = us / 54925u;
    u32 rest = us % 54925u;

    for (u32 c = 0; c < chunks; c++) {
        outb(0x43, 0xB0);
        outb(0x42, 0xFF);
        outb(0x42, 0xFF);
        u16 prev = pit_read();
        u16 wraps = 0;
        while (wraps < 1) {
            u16 now = pit_read();
            if (now > prev) wraps++;
            prev = now;
        }
    }

    if (rest > 0) {
        u32 ticks = (rest * 1193182u) / 1000000u;
        if (ticks > 0xFFFF) ticks = 0xFFFF;
        if (ticks < 2) ticks = 2;
        u16 reload = (u16)(0x10000u - ticks);
        outb(0x43, 0xB0);
        outb(0x42, (u8)(reload & 0xFF));
        outb(0x42, (u8)(reload >> 8));

        u16 prev = pit_read();
        u32 done = 0;
        while (done < ticks) {
            u16 now = pit_read();
            if (now > prev) done += (u32)(now - prev);
            else if (now < prev) done += (u32)(prev - now);
            prev = now;
        }
    }
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

static void draw_background(void) {
    for (u32 y = 0; y < scr_h; y++) {
        u32 c = bg_at((int)y);
        for (u32 x = 0; x < scr_w; x++)
            px((int)x, (int)y, c);
    }
}

static void draw_logo(int cx, int cy, int size) {
    int x0 = cx - size / 2;
    int y0 = cy - size / 2;
    for (int j = 0; j < size; j++) {
        int sy = (int)((long)j * LOGO_H / size);
        for (int i = 0; i < size; i++) {
            int sx = (int)((long)i * LOGO_W / size);
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

static int text_track(int pct) {
    int t = (6 * pct + 50) / 100;
    return t < 2 ? 2 : t;
}

static int text_width(int pct) {
    int track = text_track(pct);
    int total = 0;
    for (int i = 0; i < ASC48_TEXT_COUNT; i++)
        total += (asc48_text_table[i].w * pct + 50) / 100 + track;
    total -= track;
    return total;
}

static void draw_text_at(int y, int pct) {
    int track = text_track(pct);
    int total = text_width(pct);
    int x = (int)scr_w / 2 - total / 2;
    int h = (ASC48_CELL * pct + 50) / 100;
    if (h < 1) h = 1;

    u32 fg = pack(235, 235, 235);
    for (int i = 0; i < ASC48_TEXT_COUNT; i++) {
        const asc48_glyph_t *g = &asc48_text_table[i];
        const u8 *bits = asc48_text_bits + (u32)i * ASC48_GLYPH_BYTES;
        int gw = (g->w * pct + 50) / 100;
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

static void draw_ring_box(u32 *buf, int box, int bcx, int bcy,
                          int base_y, int r, int th, int phase, u32 color) {
    for (int j = 0; j < box; j++) {
        u32 c = bg_at(base_y + j);
        for (int i = 0; i < box; i++)
            buf[j * box + i] = c;
    }
    gfx_set_target(buf, box, box, box);
    gfx_draw_arc(bcx, bcy, r, phase, phase + 70, color, th);
    gfx_draw_arc(bcx, bcy, r, phase + 120, phase + 190, color, th);
    gfx_draw_arc(bcx, bcy, r, phase + 240, phase + 310, color, th);
    gfx_reset_target();
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

    serial_puts("[KERNEL] gfx ready, drawing boot screen\n");
    serial_puts("[KERNEL] mode ");
    serial_putnum(scr_w);
    serial_putc('x');
    serial_putnum(scr_h);
    serial_putc(' ');
    serial_putnum(fb_bpp);
    serial_puts("bpp\n");

    draw_background();
    serial_puts("[KERNEL] background done\n");

    int cx = (int)scr_w / 2;

    int k = (int)(scr_h * 100u / 600u);
    if (k < 60) k = 60;
    if (k > 150) k = 150;

    int logo_size = LOGO_H * k / 100;
    if (logo_size < 32) logo_size = 32;

    int tpct = k * TEXT_SCALE / 100;
    if (tpct < 20) tpct = 20;
    while (tpct > 20 && text_width(tpct) > (int)scr_w - 40)
        tpct--;

    int r  = (34 * k * RING_SCALE + 5000) / 10000;
    int th = (5 * k * RING_SCALE + 5000) / 10000;
    if (r < 8) r = 8;
    if (th < 2) th = 2;

    int gap1 = 30 * k / 100;
    int gap2 = 40 * k / 100;
    if (gap1 < 8) gap1 = 8;
    if (gap2 < 10) gap2 = 10;

    int text_h = (ASC48_CELL * tpct + 50) / 100;
    if (text_h < 1) text_h = 1;

    int block_h = logo_size + gap1 + text_h + gap2 + (r + th) * 2;
    int top = ((int)scr_h - block_h) / 2;
    if (top < 0) top = 0;

    int logo_cy = top + logo_size / 2;
    int text_y  = top + logo_size + gap1;
    int cy      = text_y + text_h + gap2 + r + th;

    draw_logo(cx, logo_cy, logo_size);
    draw_text_at(text_y, tpct);
    serial_puts("[KERNEL] logo + text done, spinning\n");

    int phase = 0;
    u32 white = pack(255, 255, 255);

    int box = (r + th + 3) * 2;
    if (box > RING_BOX_MAX) box = RING_BOX_MAX;
    int box_x = cx - box / 2;
    int box_y = cy - box / 2;
    static u32 ring_buf[RING_BOX_MAX * RING_BOX_MAX];
    int bcx = box / 2;
    int bcy = box / 2;

    while (1) {
        draw_ring_box(ring_buf, box, bcx, bcy, box_y, r, th, phase, white);
        gfx_blit_buffer(ring_buf, box, box_x, box_y, box, box);
        phase = (phase + ARC_STEP) % 360;
        delay_asm((u32)(ARC_DELAY * scr_h / 600u));
    }
}