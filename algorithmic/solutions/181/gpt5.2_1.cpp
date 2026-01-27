#include <bits/stdc++.h>
using namespace std;

struct FastInput {
    static constexpr size_t BUFSZ = 1 << 20;
    char buf[BUFSZ];
    size_t idx = 0, len = 0;

    inline char readChar() {
        if (idx >= len) {
            len = fread(buf, 1, BUFSZ, stdin);
            idx = 0;
            if (len == 0) return 0;
        }
        return buf[idx++];
    }

    int readInt() {
        char c;
        do {
            c = readChar();
            if (!c) return 0;
        } while (c <= ' ');

        int sign = 1;
        if (c == '-') { sign = -1; c = readChar(); }

        int x = 0;
        while (c > ' ') {
            x = x * 10 + (c - '0');
            c = readChar();
            if (!c) break;
        }
        return x * sign;
    }

    void consumeBits(long long k) {
        while (k > 0) {
            char c = readChar();
            if (!c) break;
            if (c == '0' || c == '1') --k;
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastInput in;
    int n = in.readInt();
    if (n <= 0) return 0;

    long long totalBits = 2LL * n * n;
    in.consumeBits(totalBits);

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << i;
    }
    cout << '\n';
    return 0;
}