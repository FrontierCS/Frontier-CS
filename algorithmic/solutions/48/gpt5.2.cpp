#include <bits/stdc++.h>
using namespace std;

struct Basis {
    long double ox, oy, oz; // offsets in units of a
};

struct Lattice {
    long double factorA; // a = factorA * r
    vector<Basis> basis;
};

static inline unsigned long long count_for_lattice(const Lattice& lat, long double r, unsigned long long need) {
    if (!(r > 0)) return need;
    long double L = 1.0L - 2.0L * r;
    if (L < 0) return 0;

    long double a = lat.factorA * r;
    if (!(a > 0)) return 0;

    long double q = L / a;
    __int128 total = 0;

    auto axisCount = [&](long double off) -> unsigned long long {
        long double t = q - off + 1e-12L; // tiny positive to avoid losing exact-boundary layers
        if (t < -1e-18L) return 0ULL;
        long long imax = (long long)floor(t);
        if (imax < 0) return 0ULL;
        return (unsigned long long)(imax + 1);
    };

    for (const auto& b : lat.basis) {
        unsigned long long cx = axisCount(b.ox);
        if (!cx) continue;
        unsigned long long cy = axisCount(b.oy);
        if (!cy) continue;
        unsigned long long cz = axisCount(b.oz);
        if (!cz) continue;

        __int128 add = (__int128)cx * (__int128)cy * (__int128)cz;
        total += add;
        if (total >= (__int128)need) return need;
    }

    return (unsigned long long)total;
}

static inline long double best_r_for_lattice(const Lattice& lat, unsigned long long n) {
    long double lo = 0.0L, hi = 0.5L;
    for (int it = 0; it < 90; ++it) {
        long double mid = (lo + hi) * 0.5L;
        if (count_for_lattice(lat, mid, n) >= n) lo = mid;
        else hi = mid;
    }
    return lo;
}

static inline void center_axis(vector<array<long double,3>>& pts, int ax) {
    long double mn = 1e100L, mx = -1e100L;
    for (auto &p : pts) {
        mn = min(mn, p[ax]);
        mx = max(mx, p[ax]);
    }
    long double dx = ((1.0L - mx) - mn) * 0.5L;
    if (mn + dx < 0.0L) dx -= (mn + dx);
    if (mx + dx > 1.0L) dx -= (mx + dx - 1.0L);
    for (auto &p : pts) p[ax] += dx;
}

static inline vector<array<long double,3>> generate_points(const Lattice& lat, unsigned long long n, long double r_best) {
    long double r = r_best * (1.0L - 1e-12L);
    if (!(r > 0)) r = r_best;
    if (!(r > 0)) r = 1e-9L;

    long double a = lat.factorA * r;
    long double mn = r, mx = 1.0L - r;
    long double L = mx - mn;

    vector<array<long double,3>> pts;
    pts.reserve((size_t)n);

    if (!(a > 0) || L < 0) return pts;

    long long m = (long long)floor(L / a) + 3;
    if (m < 0) m = 0;

    const long double eps = 2e-15L;

    for (long long kz = 0; kz <= m && pts.size() < n; ++kz) {
        for (long long jy = 0; jy <= m && pts.size() < n; ++jy) {
            for (long long ix = 0; ix <= m && pts.size() < n; ++ix) {
                for (const auto& b : lat.basis) {
                    long double x = mn + a * ( (long double)ix + b.ox );
                    long double y = mn + a * ( (long double)jy + b.oy );
                    long double z = mn + a * ( (long double)kz + b.oz );
                    if (x < mn - eps || x > mx + eps) continue;
                    if (y < mn - eps || y > mx + eps) continue;
                    if (z < mn - eps || z > mx + eps) continue;
                    // hard bounds (avoid rare eps overshoot)
                    if (x < 0.0L) x = 0.0L;
                    if (y < 0.0L) y = 0.0L;
                    if (z < 0.0L) z = 0.0L;
                    if (x > 1.0L) x = 1.0L;
                    if (y > 1.0L) y = 1.0L;
                    if (z > 1.0L) z = 1.0L;
                    pts.push_back({x,y,z});
                    if (pts.size() >= n) break;
                }
            }
        }
    }

    if (pts.size() == n) {
        center_axis(pts, 0);
        center_axis(pts, 1);
        center_axis(pts, 2);
    }
    return pts;
}

static inline vector<array<long double,3>> baseline_grid(unsigned long long n) {
    long long m = (long long)floor(cbrtl((long double)n));
    while ((__int128)m * m * m < (__int128)n) ++m;
    if (m < 1) m = 1;
    vector<array<long double,3>> pts;
    pts.reserve((size_t)n);
    for (long long k = 0; k < m && pts.size() < n; ++k) {
        for (long long j = 0; j < m && pts.size() < n; ++j) {
            for (long long i = 0; i < m && pts.size() < n; ++i) {
                long double x = ((long double)i + 0.5L) / (long double)m;
                long double y = ((long double)j + 0.5L) / (long double)m;
                long double z = ((long double)k + 0.5L) / (long double)m;
                pts.push_back({x,y,z});
            }
        }
    }
    return pts;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    unsigned long long n;
    if (!(cin >> n)) return 0;

    cout << setprecision(17) << defaultfloat;

    if (n == 2) {
        long double s3 = sqrtl(3.0L);
        long double t = s3 / (2.0L * (s3 + 1.0L));
        long double a1 = t, a2 = 1.0L - t;
        cout << a1 << ' ' << a1 << ' ' << a1 << "\n";
        cout << a2 << ' ' << a2 << ' ' << a2 << "\n";
        return 0;
    }

    if (n <= 8) {
        long double r = 0.25L;
        long double a = r, b = 1.0L - r;
        vector<array<long double,3>> corners;
        corners.reserve(8);
        for (int z = 0; z < 2; ++z)
            for (int y = 0; y < 2; ++y)
                for (int x = 0; x < 2; ++x)
                    corners.push_back({x?b:a, y?b:a, z?b:a});
        for (unsigned long long i = 0; i < n; ++i) {
            auto &p = corners[(size_t)i];
            cout << p[0] << ' ' << p[1] << ' ' << p[2] << "\n";
        }
        return 0;
    }

    const long double SQRT2 = sqrtl(2.0L);
    const long double SQRT3 = sqrtl(3.0L);

    Lattice SC;
    SC.factorA = 2.0L;
    SC.basis = { {0.0L, 0.0L, 0.0L} };

    Lattice BCC;
    BCC.factorA = 4.0L / SQRT3;
    BCC.basis = { {0.0L,0.0L,0.0L}, {0.5L,0.5L,0.5L} };

    Lattice FCC;
    FCC.factorA = 2.0L * SQRT2;
    FCC.basis = { {0.0L,0.0L,0.0L}, {0.0L,0.5L,0.5L}, {0.5L,0.0L,0.5L}, {0.5L,0.5L,0.0L} };

    vector<pair<long double, const Lattice*>> candidates;
    candidates.reserve(3);
    long double r_sc = best_r_for_lattice(SC, n);
    long double r_bcc = best_r_for_lattice(BCC, n);
    long double r_fcc = best_r_for_lattice(FCC, n);

    const Lattice* bestLat = &FCC;
    long double bestR = r_fcc;
    if (r_bcc > bestR) { bestR = r_bcc; bestLat = &BCC; }
    if (r_sc  > bestR) { bestR = r_sc;  bestLat = &SC;  }

    auto pts = generate_points(*bestLat, n, bestR);
    if (pts.size() != n) pts = baseline_grid(n);

    for (auto &p : pts) {
        // Ensure within bounds due to any tiny numerical drift
        if (p[0] < 0.0L) p[0] = 0.0L;
        if (p[1] < 0.0L) p[1] = 0.0L;
        if (p[2] < 0.0L) p[2] = 0.0L;
        if (p[0] > 1.0L) p[0] = 1.0L;
        if (p[1] > 1.0L) p[1] = 1.0L;
        if (p[2] > 1.0L) p[2] = 1.0L;
        cout << p[0] << ' ' << p[1] << ' ' << p[2] << "\n";
    }

    return 0;
}