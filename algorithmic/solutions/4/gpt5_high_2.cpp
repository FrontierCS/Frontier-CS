#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline int getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return EOF;
        }
        return buf[idx++];
    }
    template <typename T>
    bool nextInt(T& out) {
        int c = getChar();
        if (c == EOF) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (c == EOF) return false;
        }
        T sign = 1;
        if (c == '-') {
            sign = -1;
            c = getChar();
        }
        T x = 0;
        for (; c >= '0' && c <= '9'; c = getChar()) {
            x = x * 10 + (c - '0');
        }
        out = x * sign;
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    long long n, k;
    if (!fs.nextInt(n)) return 0;
    if (!fs.nextInt(k)) return 0;

    size_t N = (size_t)n * (size_t)n;
    vector<long long> a;
    a.reserve(N);
    for (size_t i = 0; i < N; ++i) {
        long long v;
        if (!fs.nextInt(v)) return 0;
        a.push_back(v);
    }

    nth_element(a.begin(), a.begin() + (k - 1), a.end());
    cout << a[k - 1] << "\n";
    return 0;
}