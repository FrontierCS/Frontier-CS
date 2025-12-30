#include <bits/stdc++.h>
using namespace std;

static inline long long icbrt_ceil_ll(long long n) {
    long long x = (long long)floor(cbrt((long double)n));
    while (x * x * x < n) ++x;
    while ((x - 1) > 0 && (x - 1) * (x - 1) * (x - 1) >= n) --x;
    return x;
}

static inline long long sat_mul3(long long a, long long b, long long c, long long cap) {
    __int128 v = (__int128)a * (__int128)b;
    if (v > cap) return cap;
    v *= (__int128)c;
    if (v > cap) return cap;
    return (long long)v;
}

static inline long long count_fcc(long double d, long long cap) {
    if (!(d > 0)) return cap;
    long double L = 1.0L - d;
    if (L < 0) return 0;
    long double a = d * sqrtl(2.0L);
    long double t = L / a;

    const long double eps = 1e-13L;
    long long I = (long long) floorl(t + eps);
    if (I < 0) return 0;

    long long I2 = (long long) floorl(t - 0.5L + eps);
    long long A = I + 1;
    long long cnt0 = sat_mul3(A, A, A, cap);
    if (cnt0 >= cap) return cap;
    if (I2 < 0) return cnt0;

    long long B = I2 + 1;
    long long cnt1 = sat_mul3(A, B, B, cap);
    long long total = cnt0;
    total = min(cap, total + cnt1);
    total = min(cap, total + cnt1);
    total = min(cap, total + cnt1);
    return total;
}

static vector<array<double,3>> gen_fcc(long long n, long double d_in) {
    long double d = d_in;
    for (int attempt = 0; attempt < 20; ++attempt) {
        vector<array<double,3>> pts;
        pts.reserve((size_t)n);

        if (d <= 0) d = 1e-12L;
        long double L = 1.0L - d;
        long double a = d * sqrtl(2.0L);
        long double margin = d / 2.0L;

        const long double eps = 1e-13L;
        long double t = L / a;
        long long I = (long long) floorl(t + eps);
        long long I2 = (long long) floorl(t - 0.5L + eps);

        auto addp = [&](long double x, long double y, long double z) {
            // should already be within [0,1], but keep extremely tiny safety
            double xd = (double)x, yd = (double)y, zd = (double)z;
            if (xd < 0) xd = 0; if (xd > 1) xd = 1;
            if (yd < 0) yd = 0; if (yd > 1) yd = 1;
            if (zd < 0) zd = 0; if (zd > 1) zd = 1;
            pts.push_back({xd, yd, zd});
        };

        if (I >= 0) {
            // basis (0,0,0)
            for (long long i = 0; i <= I && (long long)pts.size() < n; ++i) {
                long double x = margin + (long double)i * a;
                for (long long j = 0; j <= I && (long long)pts.size() < n; ++j) {
                    long double y = margin + (long double)j * a;
                    for (long long k = 0; k <= I && (long long)pts.size() < n; ++k) {
                        long double z = margin + (long double)k * a;
                        addp(x, y, z);
                    }
                }
            }
        }

        if (I2 >= 0) {
            long double half = 0.5L * a;
            // basis (0,1/2,1/2)
            for (long long i = 0; i <= I && (long long)pts.size() < n; ++i) {
                long double x = margin + (long double)i * a;
                for (long long j = 0; j <= I2 && (long long)pts.size() < n; ++j) {
                    long double y = margin + (long double)j * a + half;
                    for (long long k = 0; k <= I2 && (long long)pts.size() < n; ++k) {
                        long double z = margin + (long double)k * a + half;
                        addp(x, y, z);
                    }
                }
            }
            // basis (1/2,0,1/2)
            for (long long i = 0; i <= I2 && (long long)pts.size() < n; ++i) {
                long double x = margin + (long double)i * a + half;
                for (long long j = 0; j <= I && (long long)pts.size() < n; ++j) {
                    long double y = margin + (long double)j * a;
                    for (long long k = 0; k <= I2 && (long long)pts.size() < n; ++k) {
                        long double z = margin + (long double)k * a + half;
                        addp(x, y, z);
                    }
                }
            }
            // basis (1/2,1/2,0)
            for (long long i = 0; i <= I2 && (long long)pts.size() < n; ++i) {
                long double x = margin + (long double)i * a + half;
                for (long long j = 0; j <= I2 && (long long)pts.size() < n; ++j) {
                    long double y = margin + (long double)j * a + half;
                    for (long long k = 0; k <= I && (long long)pts.size() < n; ++k) {
                        long double z = margin + (long double)k * a;
                        addp(x, y, z);
                    }
                }
            }
        }

        if ((long long)pts.size() >= n) {
            pts.resize((size_t)n);
            return pts;
        }

        d *= 0.999L;
    }

    // Fallback (should not happen): simple grid
    long long M = icbrt_ceil_ll(n);
    vector<array<double,3>> pts;
    pts.reserve((size_t)n);
    for (long long i = 0; i < M && (long long)pts.size() < n; ++i) {
        double x = (i + 0.5) / (double)M;
        for (long long j = 0; j < M && (long long)pts.size() < n; ++j) {
            double y = (j + 0.5) / (double)M;
            for (long long k = 0; k < M && (long long)pts.size() < n; ++k) {
                double z = (k + 0.5) / (double)M;
                pts.push_back({x,y,z});
            }
        }
    }
    pts.resize((size_t)n);
    return pts;
}

static vector<array<double,3>> gen_sc(long long n) {
    long long M = icbrt_ceil_ll(n);
    vector<array<double,3>> pts;
    pts.reserve((size_t)n);
    for (long long i = 0; i < M && (long long)pts.size() < n; ++i) {
        double x = (i + 0.5) / (double)M;
        for (long long j = 0; j < M && (long long)pts.size() < n; ++j) {
            double y = (j + 0.5) / (double)M;
            for (long long k = 0; k < M && (long long)pts.size() < n; ++k) {
                double z = (k + 0.5) / (double)M;
                pts.push_back({x,y,z});
            }
        }
    }
    pts.resize((size_t)n);
    return pts;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    // Simple cubic baseline radius
    long long M = icbrt_ceil_ll(n);
    long double r_sc = 1.0L / (2.0L * (long double)M);

    // FCC: binary search maximal d such that count>=n, then r_fcc=d/2.
    long double lo = 0.0L, hi = 1.0L;
    for (int it = 0; it < 90; ++it) {
        long double mid = (lo + hi) / 2.0L;
        long long cnt = count_fcc(mid, n);
        if (cnt >= n) lo = mid;
        else hi = mid;
    }
    long double d_best = lo;
    // Safety shrink to avoid borderline floating issues
    long double d_use = d_best * 0.999999999999L;
    long double r_fcc = d_use / 2.0L;

    vector<array<double,3>> ans;
    if (r_fcc > r_sc) ans = gen_fcc(n, d_use);
    else ans = gen_sc(n);

    cout.setf(std::ios::fmtflags(0), std::ios::floatfield);
    cout << setprecision(17);
    for (long long i = 0; i < n; ++i) {
        cout << ans[(size_t)i][0] << ' ' << ans[(size_t)i][1] << ' ' << ans[(size_t)i][2] << '\n';
    }
    return 0;
}