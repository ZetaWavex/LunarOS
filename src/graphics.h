#ifndef GRAPHICS_H
#define GRAPHICS_H

typedef unsigned char  u8;
typedef unsigned short u16;
typedef unsigned int   u32;

typedef struct {
    u32 width;
    u32 height;
    u32 bpp;
    u32 pitch;
    u32 lfb;
} gfx_info_t;

typedef struct {
    u8 r, g, b, a;
} rgba_t;

typedef u32 color_t;

color_t rgb(u8 r, u8 g, u8 b);
color_t rgba_to_color(rgba_t px);
void gfx_init(gfx_info_t *info);
void gfx_putpixel(int x, int y, color_t c);
void gfx_fill_rect(int x, int y, int w, int h, color_t c);
void gfx_clear(color_t c);
void gfx_blit(int x, int y, int w, int h, rgba_t *data);
void gfx_draw_arc(int cx, int cy, int r, int start_a, int end_a,
                  color_t c, int thickness);
void gfx_gradient_vertical(int x, int y, int w, int h,
                           color_t c1, color_t c2);
void gfx_putchar(int x, int y, char c, color_t fg, color_t bg);
void gfx_putstr(int x, int y, const char *s, color_t fg, color_t bg);
u8 gfx_get_glyph(u8 c, int row);
void gfx_set_target(u32 *buf, int stride, int w, int h);
void gfx_reset_target(void);
void gfx_blit_buffer(u32 *buf, int stride, int x, int y, int w, int h);

extern gfx_info_t g_gfx;

#endif