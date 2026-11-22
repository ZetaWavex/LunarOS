typedef unsigned int u32;

static const u32 tbl[64] = { 1, 2, 3, 4 };
static u32 buf[256];
static int state;

void kernel_main(u32 lfb, u32 w, u32 h, u32 bpp, u32 pitch) {
    state = (int)(lfb + w + h + bpp + pitch);
    buf[0] = tbl[state & 3];
    *(volatile u32 *)0x1000 = (u32)state;
}