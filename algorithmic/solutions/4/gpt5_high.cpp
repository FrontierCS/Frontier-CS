#include <bits/stdc++.h>
using namespace std;

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
    bool next(T &out) {
        char c;
        T sign = 1;
        T val = 0;
        c = getch();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getch();
            if (!c) return false;
        }
        if (c == '-') {
            sign = -1;
            c = getch();
        }
        for (; c >= '0' && c <= '9'; c = getch()) {
            val = val * 10 + (c - '0');
        }
        out = val * sign;
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n;
    long long k;
    if (!fs.next(n)) return 0;
    if (!fs.next(k)) return 0;

    vector<long long> A;
    A.resize((size_t)n * n);
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            long long x;
            fs.next(x);
            A[(size_t)i * n + j] = x;
        }
    }

    auto countLE = [&](long long x) -> long long {
        long long cnt = 0;
        int i = n - 1, j = 0;
        while (i >= 0 && j < n) {
            if (A[(size_t)i * n + j] <= x) {
                cnt += (i + 1);
                ++j;
            } else {
                --i;
            }
        }
        return cnt;
    };

    long long lo = A[0];
    long long hi = A[(size_t)n * n - 1];

    while (lo < hi) {
        long long mid = lo + (hi - lo) / 2;
        if (countLE(mid) >= k) hi = mid;
        else lo = mid + 1;
    }

    cout << lo << '\n';
    return 0;
}