#include <bits/stdc++.h>
using namespace std;

static const size_t OUTBUF_SIZE = 1 << 20;
static char outbuf[OUTBUF_SIZE];
static size_t outptr = 0;

inline void flush_out() {
    if (outptr) {
        fwrite(outbuf, 1, outptr, stdout);
        outptr = 0;
    }
}

inline void write_char(char c) {
    if (outptr == OUTBUF_SIZE) flush_out();
    outbuf[outptr++] = c;
}

inline void write_int(int x) {
    char s[16];
    int n = 0;
    if (x == 0) {
        write_char('0');
        return;
    }
    while (x > 0) {
        s[n++] = char('0' + (x % 10));
        x /= 10;
    }
    while (n--) write_char(s[n]);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n, m;
    int k;
    long double eps;
    if (!(cin >> n >> m >> k >> eps)) return 0;

    // Assign contiguous blocks to each part: part j gets vertices in
    // [floor((j-1)*n/k), floor(j*n/k)) (1-based labels in output).
    long long start = 0;
    for (int part = 1; part <= k; ++part) {
        long long end = (long long)part * n / k;
        for (long long i = start; i < end; ++i) {
            if (i > 0) write_char(' ');
            write_int(part);
        }
        start = end;
    }
    write_char('\n');
    flush_out();
    return 0;
}