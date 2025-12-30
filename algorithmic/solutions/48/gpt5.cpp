#include <bits/stdc++.h>
using namespace std;

static inline uint64_t sat_mul(uint64_t a, uint64_t b, uint64_t cap) {
    if (a == 0 || b == 0) return 0;
    if (a > cap / max<uint64_t>(b,1)) return cap;
    uint64_t p = a * b;
    if (p > cap) return cap;
    return p;
}

static inline uint64_t sat_add(uint64_t a, uint64_t b, uint64_t cap) {
    uint64_t s = a + b;
    if (s < a || s > cap) return cap;
    return s;
}

struct FCCPack {
    static constexpr double eps = 1e-12;
    static constexpr double SQRT2 = 1.4142135623730950488;

    static uint64_t count(double d, uint64_t cap) {
        if (d <= 1e-12) return cap;
        double L = 1.0 - d;
        if (L < 0) L = 0;
        double a = d * SQRT2;

        // Number of positions at offsets 0 and 0.5 along one axis
        long long Nx0 = (long long)floor(L / a + 1e-12) + 1;
        long long Nx1 = (long long)floor((L - 0.5 * a) / a + 1e-12) + 1;
        if (Nx0 < 1) Nx0 = 1; // Always at least one (at position r)
        if (Nx1 < 0) Nx1 = 0;

        uint64_t x0 = (uint64_t)Nx0;
        uint64_t x1 = (uint64_t)Nx1;

        // Total points: x0^3 + 3*x0*x1^2
        uint64_t term1 = sat_mul(sat_mul(x0, x0, cap), x0, cap);
        uint64_t t = sat_mul(x1, x1, cap);
        t = sat_mul(t, x0, cap);
        uint64_t term2 = sat_mul(3, t, cap);
        return min(cap, sat_add(term1, term2, cap));
    }

    static void emit(double d, uint64_t need) {
        double r = 0.5 * d;
        double a = d * SQRT2;
        double L = 1.0 - d;

        long long Nx0 = (long long)floor(L / a + 1e-12) + 1;
        long long Nx1 = (long long)floor((L - 0.5 * a) / a + 1e-12) + 1;
        if (Nx0 < 1) Nx0 = 1;
        if (Nx1 < 0) Nx1 = 0;

        auto clamp01 = [](double v)->double{
            if (v < 0.0) return 0.0;
            if (v > 1.0) return 1.0;
            return v;
        };

        uint64_t printed = 0;

        auto print_point = [&](double x, double y, double z) {
            if (printed >= need) return;
            // Ensure inside [r, 1-r] with tiny safety
            double lo = r, hi = 1.0 - r;
            x = max(lo, min(hi, x));
            y = max(lo, min(hi, y));
            z = max(lo, min(hi, z));
            x = clamp01(x);
            y = clamp01(y);
            z = clamp01(z);
            printf("%.17g %.17g %.17g\n", x, y, z);
            ++printed;
        };

        // Type A: (0,0,0)
        for (long long ix=0; ix<Nx0 && printed<need; ++ix) {
            double x = r + ix * a;
            for (long long iy=0; iy<Nx0 && printed<need; ++iy) {
                double y = r + iy * a;
                for (long long iz=0; iz<Nx0 && printed<need; ++iz) {
                    double z = r + iz * a;
                    print_point(x, y, z);
                }
            }
        }

        // Type B: (0, 0.5, 0.5)
        for (long long ix=0; ix<Nx0 && printed<need; ++ix) {
            double x = r + ix * a;
            for (long long iy=0; iy<Nx1 && printed<need; ++iy) {
                double y = r + (iy + 0.5) * a;
                for (long long iz=0; iz<Nx1 && printed<need; ++iz) {
                    double z = r + (iz + 0.5) * a;
                    print_point(x, y, z);
                }
            }
        }

        // Type C: (0.5, 0, 0.5)
        for (long long ix=0; ix<Nx1 && printed<need; ++ix) {
            double x = r + (ix + 0.5) * a;
            for (long long iy=0; iy<Nx0 && printed<need; ++iy) {
                double y = r + iy * a;
                for (long long iz=0; iz<Nx1 && printed<need; ++iz) {
                    double z = r + (iz + 0.5) * a;
                    print_point(x, y, z);
                }
            }
        }

        // Type D: (0.5, 0.5, 0)
        for (long long ix=0; ix<Nx1 && printed<need; ++ix) {
            double x = r + (ix + 0.5) * a;
            for (long long iy=0; iy<Nx1 && printed<need; ++iy) {
                double y = r + (iy + 0.5) * a;
                for (long long iz=0; iz<Nx0 && printed<need; ++iz) {
                    double z = r + iz * a;
                    print_point(x, y, z);
                }
            }
        }
    }
};

struct GridPack {
    static void emit(uint64_t n) {
        // Balanced simple cubic grid with M^3 >= n
        uint64_t M = 1;
        while (M * M * M < n) ++M;
        double s = 1.0 / (double)M;
        double r = 0.5 * s;

        uint64_t printed = 0;
        for (uint64_t ix = 0; ix < M && printed < n; ++ix) {
            double x = r + ix * s;
            for (uint64_t iy = 0; iy < M && printed < n; ++iy) {
                double y = r + iy * s;
                for (uint64_t iz = 0; iz < M && printed < n; ++iz) {
                    double z = r + iz * s;
                    printf("%.17g %.17g %.17g\n", x, y, z);
                    ++printed;
                }
            }
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    uint64_t n;
    if (!(cin >> n)) return 0;

    // Compute baseline grid radius r_grid = 1/(2*M)
    uint64_t M = 1;
    while (M * M * M < n) ++M;
    double r_grid = 1.0 / (2.0 * (double)M);

    // Binary search FCC spacing d to maximize r = d/2 with count >= n
    double lo = 0.0, hi = 1.0;
    for (int it = 0; it < 70; ++it) {
        double mid = 0.5 * (lo + hi);
        uint64_t cnt = FCCPack::count(mid, n);
        if (cnt >= n) lo = mid;
        else hi = mid;
    }
    double r_fcc = 0.5 * lo;

    // Pick the better of FCC and simple grid by radius
    if (r_fcc > r_grid) {
        FCCPack::emit(lo, n);
    } else {
        GridPack::emit(n);
    }
    return 0;
}