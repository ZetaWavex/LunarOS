typedef unsigned long long u64;
static char big[64];
int f(int a, int b, int c, int d, int e) {
    int i;
    for (i = 0; i < 64; i++) big[i] = (char)(a + b + c + d + e);
    return big[a];
}
void g(int *p) { *p = 1; }