#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0, size = 0;

    inline char readChar() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template <class T>
    bool readInt(T &out) {
        char c;
        do {
            c = readChar();
            if (!c) return false;
        } while (c <= ' ');

        bool neg = false;
        if (c == '-') {
            neg = true;
            c = readChar();
        }

        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = readChar();
        }
        out = neg ? -val : val;
        return true;
    }
};

int main() {
    FastScanner fs;
    int n;
    if (!fs.readInt(n)) return 0;

    int x;
    long long total = 2LL * n * n;
    for (long long i = 0; i < total; i++) fs.readInt(x);

    for (int i = 1; i <= n; i++) {
        if (i > 1) putchar(' ');
        printf("%d", i);
    }
    putchar('\n');
    return 0;
}