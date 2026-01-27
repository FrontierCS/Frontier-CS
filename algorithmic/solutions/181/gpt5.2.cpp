#include <bits/stdc++.h>
using namespace std;

class FastScanner {
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

public:
    int nextInt() {
        char c;
        do {
            c = readChar();
            if (!c) return INT_MIN;
        } while (c <= ' ');

        int sign = 1;
        if (c == '-') { sign = -1; c = readChar(); }

        int x = 0;
        while (c > ' ') {
            x = x * 10 + (c - '0');
            c = readChar();
        }
        return x * sign;
    }
};

int main() {
    FastScanner fs;
    int n = fs.nextInt();
    if (n == INT_MIN) return 0;

    long long totalToRead = 2LL * n * n;
    for (long long k = 0; k < totalToRead; k++) {
        int v = fs.nextInt();
        if (v == INT_MIN) break;
    }

    for (int i = 1; i <= n; i++) {
        if (i > 1) putchar(' ');
        printf("%d", i);
    }
    putchar('\n');
    return 0;
}