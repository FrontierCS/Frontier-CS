#include <bits/stdc++.h>
using namespace std;

struct P3 { double x,y,z; };

static inline int iclamp(long long v, int lo, int hi){
    if(v < lo) return lo;
    if(v > hi) return hi;
    return (int)v;
}

struct HCPGenerator {
    double eps = 1e-12;

    // Generate HCP points for given r, stopping after reaching limit points (if limit > 0).
    // If store is true, points are pushed to out; otherwise only count is returned.
    long long generate(double r, long long limit, vector<P3>* out, bool store) const {
        const double sqrt3 = sqrt(3.0);
        const double sqrt83 = sqrt(8.0/3.0);
        const double h = sqrt83 * r;
        const double sqrt3r = sqrt3 * r;
        const double two_r = 2.0 * r;

        long long cnt = 0;

        for (long long L = 0;; ++L) {
            double z = r + L * h;
            if (z > 1.0 - r + eps) break;

            bool isA = (L % 2 == 0);
            double base_x = isA ? r : 2.0 * r;
            double base_y = isA ? r : r * (1.0 + sqrt3 / 3.0);

            // v range along y
            double vy_min = (r - base_y) / (sqrt3r);
            double vy_max = (1.0 - r - base_y) / (sqrt3r);
            long long v_min = (long long)ceil(vy_min - 1e-12);
            long long v_max = (long long)floor(vy_max + 1e-12);
            if (v_min > v_max) continue;

            for (long long v = v_min; v <= v_max; ++v) {
                double y = base_y + v * sqrt3r;
                double x0 = base_x + v * r;

                // u range along x
                double ux_min = (r - x0) / two_r;
                double ux_max = (1.0 - r - x0) / two_r;
                long long u_min = (long long)ceil(ux_min - 1e-12);
                long long u_max = (long long)floor(ux_max + 1e-12);
                if (u_min > u_max) continue;

                for (long long u = u_min; u <= u_max; ++u) {
                    double x = x0 + two_r * u;
                    if (x < -eps || x > 1.0 + eps || y < -eps || y > 1.0 + eps || z < -eps || z > 1.0 + eps) continue;
                    if (store) out->push_back({x,y,z});
                    ++cnt;
                    if (limit > 0 && cnt >= limit) return cnt;
                }
            }
        }
        return cnt;
    }

    // Pack n points using HCP by binary-searching r
    vector<P3> pack(int n) const {
        vector<P3> res;
        if (n <= 0) return res;

        double lo = 0.0, hi = 0.5;
        // Binary search for largest r s.t. count(r) >= n
        for (int it = 0; it < 60; ++it) {
            double mid = (lo + hi) * 0.5;
            long long c = generate(mid, n, nullptr, false); // early stop at n
            if (c >= n) lo = mid; else hi = mid;
        }
        double r = lo;

        // Generate exactly n points (or as many as available)
        res.reserve(n);
        generate(r, n, &res, true);

        // Fallback to grid if something went wrong (shouldn't happen)
        if ((int)res.size() < n) {
            res.clear();
            // Balanced grid fallback
            int a = max(1, (int)round(cbrt((double)n)));
            while ((long long)a*a*a < n) ++a;
            int m = a, k = a, l = a;
            while ((long long)m*k*l >= n && (m-1)*k*l >= n) --m;
            while ((long long)m*k*l >= n && m*(k-1)*l >= n) --k;
            while ((long long)m*k*l >= n && m*k*(l-1) >= n) --l;
            while ((long long)m*k*l < n) {
                if (m <= k && m <= l) ++m;
                else if (k <= m && k <= l) ++k;
                else ++l;
            }
            int M = max(m, max(k, l));
            double rr = 1.0 / (2.0 * M);
            for (int iz = 0; iz < l && (int)res.size() < n; ++iz) {
                double z = rr + 2*rr*iz;
                for (int iy = 0; iy < k && (int)res.size() < n; ++iy) {
                    double y = rr + 2*rr*iy;
                    for (int ix = 0; ix < m && (int)res.size() < n; ++ix) {
                        double x = rr + 2*rr*ix;
                        res.push_back({x,y,z});
                    }
                }
            }
        }

        // If more than n (should not happen due to limit), trim
        if ((int)res.size() > n) res.resize(n);
        return res;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;

    HCPGenerator gen;
    vector<P3> pts = gen.pack(n);

    cout.setf(std::ios::fixed); 
    cout << setprecision(12);
    for (const auto &p : pts) {
        double x = min(1.0, max(0.0, p.x));
        double y = min(1.0, max(0.0, p.y));
        double z = min(1.0, max(0.0, p.z));
        cout << x << " " << y << " " << z << "\n";
    }
    return 0;
}