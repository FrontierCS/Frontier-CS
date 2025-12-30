#include <bits/stdc++.h>
using namespace std;

#if defined(_WIN32) || defined(_WIN64)
#define GETC getchar
#else
#define GETC getchar_unlocked
#endif

struct FastScanner {
    inline bool readInt(int &out) {
        int c = GETC();
        while (c <= ' ') {
            if (c == EOF) return false;
            c = GETC();
        }
        int sign = 1;
        if (c == '-') {
            sign = -1;
            c = GETC();
        }
        int x = 0;
        while (c > ' ') {
            x = x * 10 + (c - '0');
            c = GETC();
        }
        out = x * sign;
        return true;
    }
} In;

struct XorShift64 {
    uint64_t s;
    explicit XorShift64(uint64_t seed) { s = seed ? seed : 0x9e3779b97f4a7c15ULL; }
    inline uint64_t next() {
        uint64_t x = s;
        x ^= x << 7;
        x ^= x >> 9;
        return s = x;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!In.readInt(n)) return 0;
    In.readInt(m);

    vector<int> pos(n + 1, 0), neg(n + 1, 0);

    int a, b, c;
    for (int i = 0; i < m; ++i) {
        In.readInt(a); In.readInt(b); In.readInt(c);
        if (a > 0) ++pos[a]; else ++neg[-a];
        if (b > 0) ++pos[b]; else ++neg[-b];
        if (c > 0) ++pos[c]; else ++neg[-c];
    }

    uint64_t seed = 1469598103934665603ULL;
    seed ^= (uint64_t)n + 0x9e3779b97f4a7c15ULL + (seed << 6) + (seed >> 2);
    seed ^= (uint64_t)m + 0x9e3779b97f4a7c15ULL + (seed << 6) + (seed >> 2);
    XorShift64 rng(seed);

    string out;
    out.reserve(n * 2 + 2);
    for (int i = 1; i <= n; ++i) {
        int bit;
        if (pos[i] > neg[i]) bit = 1;
        else if (pos[i] < neg[i]) bit = 0;
        else bit = (int)(rng.next() & 1ULL);
        out.push_back(bit ? '1' : '0');
        if (i < n) out.push_back(' ');
    }
    out.push_back('\n');
    fwrite(out.c_str(), 1, out.size(), stdout);
    return 0;
}