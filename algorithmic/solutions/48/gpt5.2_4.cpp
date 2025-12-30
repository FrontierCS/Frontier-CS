#include <bits/stdc++.h>
using namespace std;

struct BufferedWriter {
    static constexpr size_t FLUSH_THRESHOLD = 1u << 20;
    string buf;

    void appendTriple(long double x, long double y, long double z) {
        char tmp[192];
        int len = snprintf(tmp, sizeof(tmp), "%.17g %.17g %.17g\n",
                           (double)x, (double)y, (double)z);
        buf.append(tmp, tmp + len);
        if (buf.size() >= FLUSH_THRESHOLD) flush();
    }

    void flush() {
        if (!buf.empty()) {
            fwrite(buf.data(), 1, buf.size(), stdout);
            buf.clear();
        }
    }

    ~BufferedWriter() { flush(); }
};

static inline __int128 count_even_in_cube(long long T) {
    __int128 m = (__int128)T + 1;          // 0..T inclusive
    __int128 total = m * m * m;
    return (total + 1) / 2;                // even parity gets the extra when odd
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    const long double EPS = 1e-15L;
    BufferedWriter out;

    if (n == 2) {
        long double s3 = sqrtl(3.0L);
        long double r = s3 / (2.0L * (1.0L + s3));
        r *= (1.0L - EPS);
        out.appendTriple(r, r, r);
        out.appendTriple(1.0L - r, 1.0L - r, 1.0L - r);
        out.flush();
        return 0;
    }

    long long T = 0;
    while (count_even_in_cube(T) < (__int128)n) ++T;

    const long double sq2 = sqrtl(2.0L);
    long double r = 1.0L / (2.0L + sq2 * (long double)T);
    r *= (1.0L - EPS);
    long double scale = r * sq2;

    long long produced = 0;
    for (long long i = 0; i <= T && produced < n; ++i) {
        long double x = r + scale * (long double)i;
        for (long long j = 0; j <= T && produced < n; ++j) {
            long double y = r + scale * (long double)j;
            long long k = (((i + j) & 1LL) ? 1LL : 0LL);
            for (; k <= T && produced < n; k += 2) {
                long double z = r + scale * (long double)k;
                out.appendTriple(x, y, z);
                ++produced;
            }
        }
    }

    out.flush();
    return 0;
}