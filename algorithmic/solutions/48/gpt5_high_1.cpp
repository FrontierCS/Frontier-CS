#include <bits/stdc++.h>
using namespace std;

struct Point { double x, y, z; };

static inline size_t countFCC(double s) {
    const double SQRT2 = sqrt(2.0);
    const double EPS = 1e-12;
    double M = 0.5 * s * SQRT2;
    if (M > 0.5 + 1e-15) return 0;
    double low = M, high = 1.0 - M;
    if (low > high + EPS) return 0;
    size_t cnt = 0;
    for (int i = 0; ; ++i) {
        double x = low + i * s;
        if (x > high + EPS) break;
        for (int j = 0; ; ++j) {
            double y = low + j * s;
            if (y > high + EPS) break;
            for (int k = 0; ; ++k) {
                double z = low + k * s;
                if (z > high + EPS) break;
                if (((i + j + k) & 1) == 0) ++cnt;
            }
        }
    }
    return cnt;
}

static inline void generateFCC(double s, size_t need, vector<Point>& out) {
    out.clear();
    const double SQRT2 = sqrt(2.0);
    const double EPS = 1e-12;
    double M = 0.5 * s * SQRT2;
    double low = M, high = 1.0 - M;
    for (int i = 0; ; ++i) {
        double x = low + i * s;
        if (x > high + EPS) break;
        for (int j = 0; ; ++j) {
            double y = low + j * s;
            if (y > high + EPS) break;
            for (int k = 0; ; ++k) {
                double z = low + k * s;
                if (z > high + EPS) break;
                if (((i + j + k) & 1) == 0) {
                    Point p{ x, y, z };
                    // Clamp to [0,1] to be safe against tiny rounding errors
                    if (p.x < 0) p.x = 0; if (p.x > 1) p.x = 1;
                    if (p.y < 0) p.y = 0; if (p.y > 1) p.y = 1;
                    if (p.z < 0) p.z = 0; if (p.z > 1) p.z = 1;
                    out.push_back(p);
                    if (out.size() >= need) return;
                }
            }
        }
    }
}

static inline void generateCubicGrid(size_t n, vector<Point>& out) {
    out.clear();
    // Balanced cubic grid m x m x m with margin r = 1/(2m)
    long long m = 1;
    while ((long long)m * m * m < (long long)n) ++m;
    double step = 1.0 / m;
    double r = 0.5 * step;
    for (int i = 0; i < m && out.size() < n; ++i) {
        double x = r + i * step;
        for (int j = 0; j < m && out.size() < n; ++j) {
            double y = r + j * step;
            for (int k = 0; k < m && out.size() < n; ++k) {
                double z = r + k * step;
                out.push_back({x, y, z});
                if (out.size() >= n) break;
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long nll;
    if (!(cin >> nll)) return 0;
    if (nll <= 0) return 0;
    size_t n = (size_t)nll;

    vector<Point> pts;
    // Special small-n case for n=2 for better radius
    if (n == 2) {
        double t = 1.0 / (2.0 * (1.0 + 1.0 / sqrt(3.0)));
        pts.push_back({t, t, t});
        pts.push_back({1.0 - t, 1.0 - t, 1.0 - t});
    } else {
        const double SQRT2 = sqrt(2.0);
        double s_max = 1.0 / SQRT2; // when only center fits
        // Initial estimate
        double s_est = cbrt(0.5 / (double)n);
        s_est = min(s_est, s_max);
        if (s_est <= 0) s_est = 0.1;

        // Ensure lower bound s_lo yields count >= n
        double s_lo = s_est;
        size_t c = countFCC(s_lo);
        int guard = 0;
        while (c < n && s_lo > 1e-9 && guard < 200) {
            s_lo *= 0.9;
            c = countFCC(s_lo);
            ++guard;
        }
        if (c < n) {
            // Fallback to cubic grid if something went wrong
            generateCubicGrid(n, pts);
        } else {
            // Find s_hi such that count < n
            double s_hi = s_lo;
            guard = 0;
            while (countFCC(s_hi) >= n && s_hi < s_max && guard < 200) {
                s_hi *= 1.05;
                if (s_hi > s_max) s_hi = s_max;
                ++guard;
                if (s_hi == s_max) break;
            }
            // Binary search between s_lo (enough) and s_hi (not enough or max)
            for (int it = 0; it < 60; ++it) {
                double mid = 0.5 * (s_lo + s_hi);
                if (countFCC(mid) >= n) s_lo = mid;
                else s_hi = mid;
            }
            double s_final = s_lo;
            // Try to ensure we indeed have enough points due to rounding
            for (int t = 0; t < 5; ++t) {
                if (countFCC(s_final) >= n) break;
                s_final *= 0.999;
            }
            generateFCC(s_final, n, pts);
            if (pts.size() < n) {
                // Very unlikely, but fallback
                generateCubicGrid(n, pts);
            }
        }
    }

    cout.setf(std::ios::fixed); 
    cout << setprecision(12);
    for (size_t i = 0; i < n; ++i) {
        cout << pts[i].x << " " << pts[i].y << " " << pts[i].z << "\n";
    }
    return 0;
}