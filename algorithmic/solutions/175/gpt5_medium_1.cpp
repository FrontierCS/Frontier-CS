#include <cstdio>
#include <vector>
#include <cstdint>

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx = 0, size = 0;
    char buf[BUFSIZE];

    inline char getch() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template<typename T>
    bool readInt(T &out) {
        char c = getch();
        if (!c) return false;
        while (c && c != '-' && (c < '0' || c > '9')) c = getch();
        if (!c) return false;
        T sign = 1;
        if (c == '-') { sign = -1; c = getch(); }
        T val = 0;
        for (; c >= '0' && c <= '9'; c = getch()) val = val * 10 + (c - '0');
        out = val * sign;
        return true;
    }
};

int main() {
    FastScanner fs;
    int n, m;
    if (!fs.readInt(n)) return 0;
    if (!fs.readInt(m)) m = 0;

    std::vector<int> pos(n + 1, 0), neg(n + 1, 0);

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        fs.readInt(a);
        fs.readInt(b);
        fs.readInt(c);
        if (a > 0) ++pos[a]; else ++neg[-a];
        if (b > 0) ++pos[b]; else ++neg[-b];
        if (c > 0) ++pos[c]; else ++neg[-c];
    }

    for (int i = 1; i <= n; ++i) {
        int bit = (pos[i] >= neg[i]) ? 1 : 0;
        if (i > 1) putchar(' ');
        putchar(bit ? '1' : '0');
    }
    putchar('\n');
    return 0;
}