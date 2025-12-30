#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx, len;
    FastScanner() : idx(0), len(0) {}
    inline char getChar() {
        if (idx >= len) {
            len = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (len == 0) return 0;
        }
        return buf[idx++];
    }
    template <typename T>
    bool readInt(T &out) {
        char c = getChar();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (!c) return false;
        }
        T sign = 1;
        if (c == '-') {
            sign = -1;
            c = getChar();
        }
        T x = 0;
        for (; c >= '0' && c <= '9'; c = getChar())
            x = x * 10 + (c - '0');
        out = x * sign;
        return true;
    }
};

int main() {
    FastScanner fs;
    int n, m;
    if (!fs.readInt(n)) return 0;
    if (!fs.readInt(m)) return 0;

    vector<int> pos(n + 1, 0), neg(n + 1, 0);

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        fs.readInt(a);
        fs.readInt(b);
        fs.readInt(c);
        if (a > 0) ++pos[a]; else ++neg[-a];
        if (b > 0) ++pos[b]; else ++neg[-b];
        if (c > 0) ++pos[c]; else ++neg[-c];
    }

    uint64_t rng_state = chrono::steady_clock::now().time_since_epoch().count();
    auto rng = [&]() -> uint64_t {
        rng_state ^= rng_state << 7;
        rng_state ^= rng_state >> 9;
        rng_state *= 2685821657736338717ULL;
        return rng_state;
    };

    string out;
    out.reserve(n * 2 + 1);
    for (int i = 1; i <= n; ++i) {
        int val;
        if (pos[i] > neg[i]) val = 1;
        else if (pos[i] < neg[i]) val = 0;
        else val = (rng() & 1);
        out.push_back(val ? '1' : '0');
        if (i < n) out.push_back(' ');
        else out.push_back('\n');
    }
    fwrite(out.data(), 1, out.size(), stdout);
    return 0;
}