#include "graphics.h"
#include "asc16_font.h"

gfx_info_t g_gfx;

static volatile u8 *framebuffer = 0;
static u32 g_bpp = 24;

color_t rgb(u8 r, u8 g, u8 b) {
    if (g_bpp == 32) return (u32)0xFF000000 | ((u32)r << 16) | ((u32)g << 8) | b;
    if (g_bpp == 24) return ((u32)r << 16) | ((u32)g << 8) | b;
    if (g_bpp == 16) return ((u16)((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3));
    return 0;
}

color_t rgba_to_color(rgba_t px) {
    if (px.a == 0) return 0;
    return rgb(px.r, px.g, px.b);
}

void gfx_init(gfx_info_t *info) {
    g_gfx = *info;
    framebuffer = (volatile u8 *)(u32)info->lfb;
    g_bpp = info->bpp;
}

static u32 *target_buf = 0;
static int target_stride = 0;
static int target_w = 0;
static int target_h = 0;

void gfx_set_target(u32 *buf, int stride, int w, int h) {
    target_buf = buf;
    target_stride = stride;
    target_w = w;
    target_h = h;
}

void gfx_reset_target(void) {
    target_buf = 0;
}

void gfx_blit_buffer(u32 *buf, int stride, int x, int y, int w, int h) {
    for (int j = 0; j < h; j++) {
        int yy = y + j;
        if (yy < 0 || (u32)yy >= g_gfx.height) continue;
        u32 *src = buf + (u32)j * (u32)stride;
        if (g_bpp == 32) {
            u32 *dst = (u32 *)&framebuffer[(u32)yy * g_gfx.pitch + (u32)x * 4];
            for (int i = 0; i < w; i++) dst[i] = src[i];
        } else {
            for (int i = 0; i < w; i++)
                gfx_putpixel(x + i, yy, src[i]);
        }
    }
}

void gfx_putpixel(int x, int y, color_t c) {
    if (target_buf) {
        if (x < 0 || y < 0 || x >= target_w || y >= target_h) return;
        target_buf[y * target_stride + x] = c;
        return;
    }
    if (x < 0 || y < 0 || (u32)x >= g_gfx.width || (u32)y >= g_gfx.height) return;
    u32 offset = y * g_gfx.pitch + x * (g_bpp / 8);
    if (g_bpp == 32) {
        u32 *p = (u32 *)&framebuffer[offset];
        *p = c;
    } else if (g_bpp == 24) {
        framebuffer[offset + 0] = (u8)(c & 0xFF);
        framebuffer[offset + 1] = (u8)((c >> 8) & 0xFF);
        framebuffer[offset + 2] = (u8)((c >> 16) & 0xFF);
    } else if (g_bpp == 16) {
        u16 *p = (u16 *)&framebuffer[offset];
        *p = (u16)c;
    }
}

void gfx_fill_rect(int x, int y, int w, int h, color_t c) {
    if (target_buf) {
        for (int j = 0; j < h; j++) {
            int yy = y + j;
            if (yy < 0 || yy >= target_h) continue;
            for (int i = 0; i < w; i++) {
                int xx = x + i;
                if (xx < 0 || xx >= target_w) continue;
                target_buf[yy * target_stride + xx] = c;
            }
        }
        return;
    }
    if (g_bpp == 32) {
        for (int j = 0; j < h; j++) {
            u32 *row = (u32 *)&framebuffer[(y + j) * g_gfx.pitch + x * 4];
            for (int i = 0; i < w; i++) row[i] = c;
        }
        return;
    }
    for (int j = 0; j < h; j++)
        for (int i = 0; i < w; i++)
            gfx_putpixel(x + i, y + j, c);
}

void gfx_clear(color_t c) {
    gfx_fill_rect(0, 0, g_gfx.width, g_gfx.height, c);
}

void gfx_blit(int x, int y, int w, int h, rgba_t *data) {
    for (int j = 0; j < h; j++) {
        for (int i = 0; i < w; i++) {
            rgba_t px = data[j * w + i];
            if (px.a == 0) continue;
            gfx_putpixel(x + i, y + j, rgb(px.r, px.g, px.b));
        }
    }
}

void gfx_gradient_vertical(int x, int y, int w, int h,
                           color_t c1, color_t c2) {
    u8 r1 = (c1 >> 16) & 0xFF, g1 = (c1 >> 8) & 0xFF, b1 = c1 & 0xFF;
    u8 r2 = (c2 >> 16) & 0xFF, g2 = (c2 >> 8) & 0xFF, b2 = c2 & 0xFF;
    if (h <= 1) { gfx_fill_rect(x, y, w, h, c1); return; }
    for (int j = 0; j < h; j++) {
        int t = (j * 1000) / h;
        u8 r = (u8)((r1 * (1000 - t) + r2 * t) / 1000);
        u8 g = (u8)((g1 * (1000 - t) + g2 * t) / 1000);
        u8 b = (u8)((b1 * (1000 - t) + b2 * t) / 1000);
        gfx_fill_rect(x, y + j, w, 1, rgb(r, g, b));
    }
}

static const int cos_tab[91] = {
    1000, 1000,  999,  999,  998,  996,  995,  993,  990,  988,
     985,  982,  978,  974,  970,  966,  961,  956,  951,  946,
     940,  934,  927,  921,  914,  906,  899,  891,  883,  875,
     866,  857,  848,  839,  829,  819,  809,  799,  788,  777,
     766,  755,  743,  731,  719,  707,  695,  682,  669,  656,
     643,  629,  616,  602,  588,  574,  559,  545,  530,  515,
     500,  485,  469,  454,  438,  423,  407,  391,  375,  358,
     342,  326,  309,  292,  276,  259,  242,  225,  208,  191,
     174,  156,  139,  122,  105,   87,   70,   52,   35,   17,
       0
};

static const int sin_tab[91] = {
       0,   17,   35,   52,   70,   87,  105,  122,  139,  156,
     174,  191,  208,  225,  242,  259,  276,  292,  309,  326,
     342,  358,  375,  391,  407,  423,  438,  454,  469,  485,
     500,  515,  530,  545,  559,  574,  588,  602,  616,  629,
     643,  656,  669,  682,  695,  707,  719,  731,  743,  755,
     766,  777,  788,  799,  809,  819,  829,  839,  848,  857,
     866,  875,  883,  891,  899,  906,  914,  921,  927,  934,
     940,  946,  951,  956,  961,  966,  970,  974,  978,  982,
     985,  988,  990,  993,  995,  996,  998,  999,  999, 1000,
    1000
};

static int cos_of(int a) {
    a %= 360;
    if (a < 0) a += 360;
    if (a <= 90) return cos_tab[a];
    if (a <= 180) return -cos_tab[180 - a];
    if (a <= 270) return -cos_tab[a - 180];
    return cos_tab[360 - a];
}

static int sin_of(int a) {
    a %= 360;
    if (a < 0) a += 360;
    if (a <= 90) return sin_tab[a];
    if (a <= 180) return sin_tab[180 - a];
    if (a <= 270) return -sin_tab[a - 180];
    return -sin_tab[360 - a];
}

static int cos_q4(int q4) {
    int d = q4 >> 2;
    int f = q4 & 3;
    int a0 = cos_of(d);
    int a1 = cos_of(d + 1);
    return a0 + ((a1 - a0) * f) / 4;
}

static int sin_q4(int q4) {
    int d = q4 >> 2;
    int f = q4 & 3;
    int a0 = sin_of(d);
    int a1 = sin_of(d + 1);
    return a0 + ((a1 - a0) * f) / 4;
}

void gfx_draw_arc(int cx, int cy, int r, int start_a, int end_a,
                  color_t c, int thickness) {
    int span = end_a - start_a;
    if (span < 0) span += 360;
    if (span == 0) span = 360;
    if (span > 360) span = 360;

    int r_outer = r + thickness / 2;
    int r_inner = r - thickness / 2;
    if (r_inner < 1) r_inner = 1;

    for (int rad = r_inner; rad <= r_outer; rad++) {
        int steps = (span * rad) / 57 + 1;
        if (steps < span) steps = span;
        for (int k = 0; k <= steps; k++) {
            int q4 = (start_a * 4) + (span * 4 * k) / steps;
            int x = (int)(((long)cos_q4(q4) * rad) / 1000);
            int y = (int)(((long)sin_q4(q4) * rad) / 1000);
            gfx_putpixel(cx + x, cy + y, c);
        }
    }
}

static int font_ready = 0;

static void build_font(void) {
    font_ready = 1;
}

u8 gfx_get_glyph(u8 c, int row) {
    if (!font_ready) build_font();
    if (c < ASC16_FIRST || c > ASC16_LAST) return 0;
    if (row < 0 || row >= ASC16_H) return 0;
    return asc16_font[(c - ASC16_FIRST) * ASC16_H + row];
}

void gfx_putchar(int x, int y, char c, color_t fg, color_t bg) {
    if (!font_ready) build_font();
    if ((u32)x + ASC16_W > g_gfx.width || (u32)y + ASC16_H > g_gfx.height) return;
    for (int row = 0; row < ASC16_H; row++) {
        u8 bits = gfx_get_glyph((u8)c, row);
        for (int col = 0; col < ASC16_W; col++) {
            if (bits & 0x80)
                gfx_putpixel(x + col, y + row, fg);
            else if (bg != 0xFFFFFFFF)
                gfx_putpixel(x + col, y + row, bg);
            bits <<= 1;
        }
    }
}

void gfx_putstr(int x, int y, const char *s, color_t fg, color_t bg) {
    while (*s) {
        gfx_putchar(x, y, *s, fg, bg);
        x += ASC16_W;
        s++;
    }
}