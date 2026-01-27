#include <bits/stdc++.h>
using namespace std;

struct FastInput {
    static const int S = 1 << 20;
    int idx, size;
    char buf[S];
    FastInput() : idx(0), size(0) {}
    inline char read() {
        if (idx >= size) {
            size = (int)fread(buf, 1, S, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template <typename T>
    bool nextInt(T &out) {
        char c = read();
        if (!c) return false;
        T sign = 1;
        T val = 0;
        while (c != '-' && (c < '0' || c > '9')) {
            c = read();
            if (!c) return false;
        }
        if (c == '-') { sign = -1; c = read(); }
        for (; c >= '0' && c <= '9'; c = read()) {
            val = val * 10 + (c - '0');
        }
        out = val * sign;
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    FastInput in;
    int n; long long m;
    if (!in.nextInt(n)) return 0;
    in.nextInt(m);
    vector<int> pos(n + 1, 0), neg(n + 1, 0);
    int a, b, c;
    for (long long i = 0; i < m; ++i) {
        in.nextInt(a); in.nextInt(b); in.nextInt(c);
        if (a > 0) ++pos[a]; else ++neg[-a];
        if (b > 0) ++pos[b]; else ++neg[-b];
        if (c > 0) ++pos[c]; else ++neg[-c];
    }
    string out;
    out.reserve(n * 2);
    for (int i = 1; i <= n; ++i) {
        out += (pos[i] >= neg[i]) ? '1' : '0';
        if (i < n) out += ' ';
    }
    out += '\n';
    fwrite(out.c_str(), 1, out.size(), stdout);
    return 0;
}