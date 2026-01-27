#include <bits/stdc++.h>
using namespace std;

struct P { double x,y,z; };

static const double SQRT2 = 1.4142135623730950488;
static const double EPS = 1e-12;

long long countFCC(double s, long long cap) {
    if (!(s > 0) || !isfinite(s)) return 0;
    double r = s / (2.0 * SQRT2);
    if (r < 0 || r > 0.5) return 0;
    double inner = 1.0 - 2.0 * r;
    if (inner < 0) return 0;
    double L = inner / s;

    // FCC offsets
    const double off[4][3] = {
        {0.0, 0.0, 0.0},
        {0.0, 0.5, 0.5},
        {0.5, 0.0, 0.5},
        {0.5, 0.5, 0.0}
    };

    long long total = 0;
    for (int p = 0; p < 4; ++p) {
        long long nx = (long long)floor(L - off[p][0] + EPS) + 1;
        long long ny = (long long)floor(L - off[p][1] + EPS) + 1;
        long long nz = (long long)floor(L - off[p][2] + EPS) + 1;
        if (nx < 0) nx = 0;
        if (ny < 0) ny = 0;
        if (nz < 0) nz = 0;
        long long add;
        // Prevent overflow by capping intermediate multiplications
        if (nx == 0 || ny == 0 || nz == 0) add = 0;
        else {
            long double mult = (long double)nx * (long double)ny;
            if (mult > (long double)(cap + 1)) mult = (long double)(cap + 1);
            mult *= (long double)nz;
            if (mult > (long double)(cap + 1)) mult = (long double)(cap + 1);
            add = (long long)mult;
        }
        total += add;
        if (total > cap) return cap + 1;
    }
    return total;
}

vector<P> generateFCC(double s, long long need) {
    vector<P> out;
    out.reserve((size_t)need);
    double r = s / (2.0 * SQRT2);
    double inner = 1.0 - 2.0 * r;
    if (inner < 0) return out;
    double L = inner / s;

    const double off[4][3] = {
        {0.0, 0.0, 0.0},
        {0.0, 0.5, 0.5},
        {0.5, 0.0, 0.5},
        {0.5, 0.5, 0.0}
    };

    for (int p = 0; p < 4 && (long long)out.size() < need; ++p) {
        long long ix_max = (long long)floor(L - off[p][0] + EPS);
        long long iy_max = (long long)floor(L - off[p][1] + EPS);
        long long iz_max = (long long)floor(L - off[p][2] + EPS);
        if (ix_max < 0 || iy_max < 0 || iz_max < 0) continue;
        for (long long i = 0; i <= ix_max && (long long)out.size() < need; ++i) {
            double x = r + s * (i + off[p][0]);
            if (x < -EPS || x > 1.0 + EPS) continue;
            if (x < 0) x = 0;
            if (x > 1) x = 1;
            for (long long j = 0; j <= iy_max && (long long)out.size() < need; ++j) {
                double y = r + s * (j + off[p][1]);
                if (y < -EPS || y > 1.0 + EPS) continue;
                if (y < 0) y = 0;
                if (y > 1) y = 1;
                for (long long k = 0; k <= iz_max && (long long)out.size() < need; ++k) {
                    double z = r + s * (k + off[p][2]);
                    if (z < -EPS || z > 1.0 + EPS) continue;
                    if (z < 0) z = 0;
                    if (z > 1) z = 1;
                    out.push_back({x, y, z});
                    if ((long long)out.size() >= need) break;
                }
            }
        }
    }
    return out;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long n;
    if (!(cin >> n)) return 0;

    if (n <= 0) return 0;

    // Initial guess for s from asymptotic N ~ 4/s^3 ignoring boundary
    double s0 = pow(4.0 / max(1.0, (double)n), 1.0 / 3.0);
    s0 = min(1.0, max(1e-6, s0));

    long long c0 = countFCC(s0, n);
    double s_low, s_high;

    if (c0 >= n) {
        s_low = s0;
        s_high = s0;
        int iter = 0;
        while (countFCC(s_high, n) >= n && s_high < 2.0 && iter++ < 60) s_high *= 1.1;
        if (countFCC(s_high, n) >= n) {
            // ensure s_high provides fewer than n points
            int safe = 0;
            while (countFCC(s_high, n) >= n && s_high < 10.0 && safe++ < 200) s_high *= 1.2;
            if (countFCC(s_high, n) >= n) s_high = s_low * 1.0001;
        }
    } else {
        s_high = s0;
        s_low = s0;
        int iter = 0;
        while (countFCC(s_low, n) < n && s_low > 1e-12 && iter++ < 60) s_low *= 0.9;
        int safe = 0;
        while (countFCC(s_low, n) < n && s_low > 1e-18 && safe++ < 200) s_low *= 0.5;
        if (countFCC(s_low, n) < n) {
            // extreme fallback
            s_low = 1e-6;
        }
        if (countFCC(s_low, n) < n) {
            // As a last resort, just output evenly spaced along diagonal
            cout.setf(std::ios::fixed); cout<<setprecision(12);
            for (long long i = 0; i < n; ++i) {
                double t = (i + 0.5) / n;
                if (t < 0) t = 0;
                if (t > 1) t = 1;
                cout << t << " " << t << " " << t << "\n";
            }
            return 0;
        }
    }

    // Binary search for maximal s with count >= n
    for (int it = 0; it < 50; ++it) {
        double mid = 0.5 * (s_low + s_high);
        long long c = countFCC(mid, n);
        if (c >= n) s_low = mid;
        else s_high = mid;
    }
    double s_final = s_low;

    // Ensure we really have >= n (compensate any rounding)
    int guard = 0;
    while (countFCC(s_final, n) < n && guard++ < 50) s_final *= 0.999;

    vector<P> pts = generateFCC(s_final, n);
    if ((long long)pts.size() < n) {
        // Slightly shrink s until enough points
        int tries = 0;
        while ((long long)pts.size() < n && tries++ < 200) {
            s_final *= 0.995;
            pts = generateFCC(s_final, n);
        }
    }

    // If still not enough (very unlikely), fill with simple grid
    if ((long long)pts.size() < n) {
        long long remain = n - (long long)pts.size();
        long long m = ceil(cbrt((double)remain));
        if (m < 1) m = 1;
        for (long long i = 0; i < m && (long long)pts.size() < n; ++i) {
            for (long long j = 0; j < m && (long long)pts.size() < n; ++j) {
                for (long long k = 0; k < m && (long long)pts.size() < n; ++k) {
                    double x = (i + 0.5) / m;
                    double y = (j + 0.5) / m;
                    double z = (k + 0.5) / m;
                    pts.push_back({x,y,z});
                }
            }
        }
    }

    cout.setf(std::ios::fixed);
    cout << setprecision(12);
    for (long long i = 0; i < n; ++i) {
        P &p = pts[i];
        double x = min(1.0, max(0.0, p.x));
        double y = min(1.0, max(0.0, p.y));
        double z = min(1.0, max(0.0, p.z));
        cout << x << " " << y << " " << z << "\n";
    }
    return 0;
}