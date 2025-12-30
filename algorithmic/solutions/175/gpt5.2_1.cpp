#include <bits/stdc++.h>
using namespace std;

static inline int readInt() {
    int c = getchar_unlocked();
    while (c <= ' ' && c != EOF) c = getchar_unlocked();
    int sgn = 1;
    if (c == '-') { sgn = -1; c = getchar_unlocked(); }
    int x = 0;
    while (c > ' ') {
        x = x * 10 + (c - '0');
        c = getchar_unlocked();
    }
    return x * sgn;
}

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed) : x(seed) {}
    uint64_t next() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n = readInt();
    int m = readInt();
    (void)m;

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)&seed;
    SplitMix64 rng(seed);

    for (int i = 1; i <= n; i++) {
        int v = (int)(rng.next() & 1ULL);
        if (i > 1) putchar_unlocked(' ');
        putchar_unlocked(v ? '1' : '0');
    }
    putchar_unlocked('\n');
    return 0;
}