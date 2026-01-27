#include <bits/stdc++.h>
using namespace std;

struct Pt { double x, y, z; };

static inline long long countFCC(double s, long long cap) {
    if (s <= 0) return LLONG_MAX;
    const double sqrt3 = sqrt(3.0);
    const double t = (sqrt3 * 0.5) * s;                // in-plane vertical spacing
    const double h = sqrt(2.0 / 3.0) * s;              // layer spacing
    const double eps = 1e-12;

    double bx[3], by[3];
    bx[0] = s * 0.5;         by[0] = s * 0.5;                // A
    bx[1] = s * 1.0;         by[1] = s * 0.5 + t / 3.0;      // B
    bx[2] = s * 1.5;         by[2] = s * 0.5 + 2.0 * t / 3.0;// C

    long long cnt = 0;
    double z0 = s * 0.5;

    long long kmin = 0;
    long long kmax = (long long)floor(((1.0 - s) + eps) / h);
    for (long long k = kmin; k <= kmax; ++k) {
        if (cap > 0 && cnt >= cap) break;
        int type = (int)((k % 3 + 3) % 3);
        double bX = bx[type], bY = by[type];

        double jmin_d = (s * 0.5 - bY) / t;
        double jmax_d = (1.0 - s * 0.5 - bY) / t;
        long long jmin = (long long)ceil(jmin_d - eps);
        long long jmax = (long long)floor(jmax_d + eps);
        if (jmax < jmin) continue;

        for (long long j = jmin; j <= jmax; ++j) {
            if (cap > 0 && cnt >= cap) break;
            double x_base = bX + j * (s * 0.5);
            double imin_d = (s * 0.5 - x_base) / s;
            double imax_d = (1.0 - s * 0.5 - x_base) / s;
            long long imin = (long long)ceil(imin_d - eps);
            long long imax = (long long)floor(imax_d + eps);
            if (imax < imin) continue;
            cnt += (imax - imin + 1);
        }
    }
    return cnt;
}

static inline vector<Pt> generateFCC(double s, long long need) {
    vector<Pt> pts;
    pts.reserve((size_t)need);
    const double sqrt3 = sqrt(3.0);
    const double t = (sqrt3 * 0.5) * s;
    const double h = sqrt(2.0 / 3.0) * s;
    const double eps = 1e-12;

    double bx[3], by[3];
    bx[0] = s * 0.5;         by[0] = s * 0.5;                // A
    bx[1] = s * 1.0;         by[1] = s * 0.5 + t / 3.0;      // B
    bx[2] = s * 1.5;         by[2] = s * 0.5 + 2.0 * t / 3.0;// C

    double z0 = s * 0.5;
    long long kmin = 0;
    long long kmax = (long long)floor(((1.0 - s) + eps) / h);

    for (long long k = kmin; k <= kmax; ++k) {
        if ((long long)pts.size() >= need) break;
        int type = (int)((k % 3 + 3) % 3);
        double bX = bx[type], bY = by[type];
        double z = z0 + k * h;

        double jmin_d = (s * 0.5 - bY) / t;
        double jmax_d = (1.0 - s * 0.5 - bY) / t;
        long long jmin = (long long)ceil(jmin_d - eps);
        long long jmax = (long long)floor(jmax_d + eps);
        if (jmax < jmin) continue;

        for (long long j = jmin; j <= jmax; ++j) {
            if ((long long)pts.size() >= need) break;
            double y = bY + j * t;
            double x_base = bX + j * (s * 0.5);
            double imin_d = (s * 0.5 - x_base) / s;
            double imax_d = (1.0 - s * 0.5 - x_base) / s;
            long long imin = (long long)ceil(imin_d - eps);
            long long imax = (long long)floor(imax_d + eps);
            if (imax < imin) continue;

            for (long long i = imin; i <= imax; ++i) {
                if ((long long)pts.size() >= need) break;
                double x = x_base + i * s;
                Pt p{min(max(x, 0.0), 1.0), min(max(y, 0.0), 1.0), min(max(z, 0.0), 1.0)};
                pts.push_back(p);
            }
        }
    }
    return pts;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    if (n <= 0) return 0;
    if (n == 1) {
        cout.setf(std::ios::fixed);
        cout << setprecision(12);
        cout << 0.5 << " " << 0.5 << " " << 0.5 << "\n";
        return 0;
    }

    double lo = 0.0, hi = 1.0;
    for (int it = 0; it < 60; ++it) {
        double mid = 0.5 * (lo + hi);
        long long c = countFCC(mid, n);
        if (c >= n) lo = mid; else hi = mid;
    }
    double s = lo;
    // Ensure we have enough points (robustness against rounding)
    long long cfinal = countFCC(s, n);
    if (cfinal < n) {
        // Slightly shrink s to increase count
        double l = 0.0, r = s;
        for (int it = 0; it < 60; ++it) {
            double mid = 0.5 * (l + r);
            long long c = countFCC(mid, n);
            if (c >= n) r = mid; else l = mid;
        }
        s = r;
    }

    vector<Pt> pts = generateFCC(s, n);
    if ((long long)pts.size() < n) {
        // Fallback: further shrink s a bit and regenerate
        double l = 0.0, r = s;
        for (int it = 0; it < 60; ++it) {
            double mid = 0.5 * (l + r);
            long long c = countFCC(mid, n);
            if (c >= n) r = mid; else l = mid;
        }
        s = r;
        pts = generateFCC(s, n);
    }

    cout.setf(std::ios::fixed);
    cout << setprecision(12);
    for (long long i = 0; i < n; ++i) {
        Pt &p = pts[i];
        double x = min(max(p.x, 0.0), 1.0);
        double y = min(max(p.y, 0.0), 1.0);
        double z = min(max(p.z, 0.0), 1.0);
        cout << x << " " << y << " " << z << "\n";
    }
    return 0;
}