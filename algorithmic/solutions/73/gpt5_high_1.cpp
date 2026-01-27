#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const size_t BUFSIZE = 1 << 20;
    int idx = 0, size = 0;
    char buf[BUFSIZE];

    inline void refill() {
        size = (int)fread(buf, 1, BUFSIZE, stdin);
        idx = 0;
    }

    bool readInt(int &out) {
        out = 0;
        int sign = 1;
        char c;
        do {
            if (idx >= size) {
                refill();
                if (size == 0) return false;
            }
            c = buf[idx++];
        } while (c <= ' ');
        if (c == '-') {
            sign = -1;
            if (idx >= size) {
                refill();
                if (size == 0) return false;
            }
            c = buf[idx++];
        }
        int val = 0;
        while (c >= '0' && c <= '9') {
            val = val * 10 + (c - '0');
            if (idx >= size) {
                refill();
                if (size == 0) break;
            }
            c = buf[idx++];
        }
        out = val * sign;
        return true;
    }
};

int main() {
    FastScanner fs;
    int n;
    if (!fs.readInt(n)) return 0;

    int W = n + 2;
    vector<uint8_t> F(W * W, 0);

    for (int i = 1; i <= n - 1; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            int x = 0;
            fs.readInt(x);
            F[i * W + j] = (uint8_t)(x & 1);
        }
    }

    vector<int> colSum(n + 1, 0);
    vector<int> p(n + 1, 0);

    for (int i = 1; i <= n - 1; ++i) {
        int prevS = 0;
        int sumRow = 0;
        for (int j = i + 1; j <= n; ++j) {
            int currS = (F[i * W + j] ^ F[(i + 1) * W + j]);
            int pij = currS ^ prevS;
            prevS = currS;
            sumRow += pij;
            colSum[j] += pij;
        }
        p[i] = 1 + ((i - 1) - colSum[i]) + sumRow;
    }
    p[n] = 1 + ((n - 1) - colSum[n]);

    for (int i = 1; i <= n; ++i) {
        if (i > 1) putchar(' ');
        printf("%d", p[i]);
    }
    putchar('\n');
    return 0;
}