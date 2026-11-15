#include "graphics.h"
#include "asc48_lunaros.h"
#include "logo_data.h"

extern void delay_asm(u32 n);

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

static void serial_puts(const char *s) {
    while (*s) serial_putc(*s++);
}

static u8 *fb;
static u32 fb_pitch;
static u32 fb_bpp;
static u32 scr_w;
static u32 scr_h;

static u32 pack(u8 r, u8 g, u8 b) {
    if (fb_bpp == 32) return ((u32)r << 16) | ((u32)g << 8) | (u32)b;
    if (fb_bpp == 24) return ((u32)b << 16) | ((u32)g << 8) | (u32)r;
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

static void draw_logo(int cx, int cy) {
    int x0 = cx - LOGO_W / 2;
    int y0 = cy - LOGO_H / 2;
    for (int j = 0; j < LOGO_H; j++) {
        for (int i = 0; i < LOGO_W; i++) {
            u8 idx = logo_idx[j * LOGO_W + i];
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

static void draw_text_at(int y) {
    int cell = ASC48_CELL;
    int track = 6;
    int total = 0;
    for (int i = 0; i < ASC48_TEXT_COUNT; i++)
        total += asc48_text_table[i].w + track;
    total -= track;

    int x = (int)scr_w / 2 - total / 2;

    u32 fg = pack(235, 235, 235);
    for (int i = 0; i < ASC48_TEXT_COUNT; i++) {
        const asc48_glyph_t *g = &asc48_text_table[i];
        const u8 *bits = asc48_text_bits + (u32)i * ASC48_GLYPH_BYTES;
        for (int row = 0; row < cell; row++) {
            for (int col = 0; col < g->w; col++) {
                int sx = g->x0 + col;
                u8 b = bits[row * ASC48_ROW_BYTES + (sx >> 3)];
                if (b & (0x80 >> (sx & 7)))
                    px(x + col, y + row, fg);
            }
        }
        x += g->w + track;
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

    draw_background();
    serial_puts("[KERNEL] background done\n");

    int cx = (int)scr_w / 2;
    int r = 34;
    int th = 5;
    int gap_logo_text = 30;
    int gap_text_ring = 40;

    int block_h = LOGO_H + gap_logo_text + ASC48_CELL + gap_text_ring
                  + (r + th) * 2;
    int top = ((int)scr_h - block_h) / 2;

    int logo_cy = top + LOGO_H / 2;
    int text_y  = top + LOGO_H + gap_logo_text;
    int cy      = text_y + ASC48_CELL + gap_text_ring + r + th;

    draw_logo(cx, logo_cy);
    draw_text_at(text_y);
    serial_puts("[KERNEL] logo + text done, spinning\n");

    int phase = 0;
    u32 white = pack(255, 255, 255);

    int box = (r + th + 3) * 2;
    int box_x = cx - r - th - 3;
    int box_y = cy - r - th - 3;
    static u32 ring_buf[96 * 96];
    int bcx = r + th + 3;
    int bcy = r + th + 3;

    while (1) {
        draw_ring_box(ring_buf, box, bcx, bcy, box_y, r, th, phase, white);
        gfx_blit_buffer(ring_buf, box, box_x, box_y, box, box);
        phase = (phase + 15) % 360;
        delay_asm(12000);
    }
}