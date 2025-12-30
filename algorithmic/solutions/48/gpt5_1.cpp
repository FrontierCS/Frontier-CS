#include <bits/stdc++.h>
using namespace std;

static const double EPS = 1e-12;

inline long long floor_ll(double x) { return (long long)floor(x + 1e-12); }
inline long long ceil_ll(double x)  { return (long long)ceil(x - 1e-12); }

struct P3 { double x, y, z; };

// Count how many HCP points fit for given r
long long count_hcp(double r, long long cap = LLONG_MAX) {
    if (!(r > 0)) return 0;
    double s_row = sqrt(3.0) * r;
    double two_r = 2.0 * r;
    double h = sqrt(8.0 / 3.0) * r;

    double zmin = r, zmax = 1.0 - r;
    if (zmin > zmax + EPS) return 0;

    long long total = 0;
    for (long long l = 0;; ++l) {
        double z = zmin + l * h;
        if (z > zmax + EPS) break;

        // Layer offset: A (even) and B (odd)
        double x0 = r;
        double y0 = r;
        if (l & 1) {
            x0 = 2.0 * r;
            y0 = r + s_row / 3.0;
        }

        // y rows
        double ymin = r, ymax = 1.0 - r;
        long long vmin = max(0LL, ceil_ll((ymin - y0) / s_row));
        long long vmax = floor_ll((ymax - y0) / s_row);
        if (vmax < vmin) continue;

        for (long long v = vmin; v <= vmax; ++v) {
            double y = y0 + v * s_row;
            (void)y;

            double x_base = x0 + v * r;
            double xmin = r, xmax = 1.0 - r;

            long long umin = ceil_ll((xmin - x_base) / two_r);
            long long umax = floor_ll((xmax - x_base) / two_r);
            if (umax < umin) continue;

            long long add = umax - umin + 1;
            total += add;
            if (total >= cap) return cap;
        }
    }
    return total;
}

// Generate up to n HCP points for given r
void generate_hcp(double r, long long n, vector<P3>& out) {
    out.clear();
    out.reserve((size_t)n);
    double s_row = sqrt(3.0) * r;
    double two_r = 2.0 * r;
    double h = sqrt(8.0 / 3.0) * r;

    double zmin = r, zmax = 1.0 - r;

    for (long long l = 0;; ++l) {
        double z = zmin + l * h;
        if (z > zmax + EPS) break;

        double x0 = r;
        double y0 = r;
        if (l & 1) {
            x0 = 2.0 * r;
            y0 = r + s_row / 3.0;
        }

        double ymin = r, ymax = 1.0 - r;
        long long vmin = max(0LL, ceil_ll((ymin - y0) / s_row));
        long long vmax = floor_ll((ymax - y0) / s_row);
        if (vmax < vmin) continue;

        for (long long v = vmin; v <= vmax; ++v) {
            double y = y0 + v * s_row;
            double x_base = x0 + v * r;

            double xmin = r, xmax = 1.0 - r;
            long long umin = ceil_ll((xmin - x_base) / two_r);
            long long umax = floor_ll((xmax - x_base) / two_r);
            if (umax < umin) continue;

            for (long long u = umin; u <= umax; ++u) {
                double x = x_base + two_r * u;
                out.push_back(P3{ x, y, z });
                if ((long long)out.size() >= n) return;
            }
        }
    }
}

// Find maximal r for which count_hcp(r) >= n using binary search
double find_r_hcp(long long n) {
    // Establish bounds
    double hi = 0.5; // infeasible for n>=2
    double lo = hi;
    while (count_hcp(lo, n) < n) {
        lo *= 0.5;
        if (lo < 1e-6) break; // safe guard; for n<=4096, r won't be this small
    }
    // If still not feasible (shouldn't happen), push lower a bit more
    while (count_hcp(lo, n) < n) {
        lo *= 0.8;
        if (lo < 1e-8) break;
    }
    // Binary search
    for (int it = 0; it < 50; ++it) {
        double mid = 0.5 * (lo + hi);
        if (count_hcp(mid, n) >= n) lo = mid;
        else hi = mid;
    }
    // Slightly reduce to avoid borderline numerical issues
    return max(0.0, lo * (1.0 - 1e-12));
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long n;
    if (!(cin >> n)) return 0;

    // Use HCP packing with radius determined by bisection
    double r = find_r_hcp(n);

    vector<P3> pts;
    generate_hcp(r, n, pts);

    // In extreme edge cases due to numerical issues, if fewer points generated,
    // slightly reduce r and regenerate
    if ((long long)pts.size() < n) {
        r *= 0.999999;
        generate_hcp(r, n, pts);
    }

    cout.setf(std::ios::fixed);
    cout << setprecision(12);
    for (long long i = 0; i < n; ++i) {
        P3 p = pts[i];
        // Clamp just in case of tiny floating drift
        double x = min(1.0, max(0.0, p.x));
        double y = min(1.0, max(0.0, p.y));
        double z = min(1.0, max(0.0, p.z));
        cout << x << " " << y << " " << z << "\n";
    }
    return 0;
}