#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct HCPGenerator {
    int n;
    static constexpr double EPS = 1e-12;

    inline long long count_points(double s, int limit) const {
        if (s <= 0) return (long long)1e18;
        double r = s * 0.5;
        double L = 1.0 - 2.0 * r;
        if (L < -1e-15) return 0;
        double sy = s * sqrt(3.0) * 0.5;
        double sz = s * sqrt(2.0 / 3.0);
        if (sy <= 0 || sz <= 0) return 0;

        auto floord = [](double x) -> long long {
            return (long long)floor(x + 1e-12);
        };

        long long cnt = 0;
        long long kz = floord(L / sz) + 1;
        for (long long k = 0; k < kz; ++k) {
            int t = (int)(k & 1);
            double y_shift = (t ? sy / 3.0 : 0.0);
            double maxYspan = L - y_shift;
            if (maxYspan < -1e-15) continue;
            long long ky = floord(maxYspan / sy) + 1;
            for (long long j = 0; j < ky; ++j) {
                double base_x = (t ? s * 0.5 : 0.0) + ((j & 1) ? s * 0.5 : 0.0);
                double maxXspan = L - base_x;
                if (maxXspan < -1e-15) continue;
                long long kx = floord(maxXspan / s) + 1;
                cnt += kx;
                if (cnt >= limit) return cnt;
            }
        }
        return cnt;
    }

    void generate_and_print(double s) const {
        double r = s * 0.5;
        double L = 1.0 - 2.0 * r;
        double sy = s * sqrt(3.0) * 0.5;
        double sz = s * sqrt(2.0 / 3.0);

        int remaining = n;

        auto floord = [](double x) -> long long {
            return (long long)floor(x + 1e-12);
        };

        long long kz = floord(L / sz) + 1;
        cout.setf(std::ios::fmtflags(0), std::ios::floatfield);
        cout << setprecision(17);
        for (long long k = 0; k < kz && remaining > 0; ++k) {
            int t = (int)(k & 1);
            double z = r + k * sz;
            if (z < -1e-14 || z > 1.0 + 1e-14) continue;

            double y_shift = (t ? sy / 3.0 : 0.0);
            double maxYspan = L - y_shift;
            if (maxYspan < -1e-15) continue;
            long long ky = floord(maxYspan / sy) + 1;

            for (long long j = 0; j < ky && remaining > 0; ++j) {
                double y = r + y_shift + j * sy;
                if (y < -1e-14 || y > 1.0 + 1e-14) continue;

                double base_x = (t ? s * 0.5 : 0.0) + ((j & 1) ? s * 0.5 : 0.0);
                double maxXspan = L - base_x;
                if (maxXspan < -1e-15) continue;
                long long kx = floord(maxXspan / s) + 1;

                for (long long i = 0; i < kx && remaining > 0; ++i) {
                    double x = r + base_x + i * s;
                    if (x >= -1e-12 && x <= 1.0 + 1e-12 &&
                        y >= -1e-12 && y <= 1.0 + 1e-12 &&
                        z >= -1e-12 && z <= 1.0 + 1e-12) {
                        // Clamp softly to [0,1] to avoid tiny rounding drift
                        double xc = min(1.0, max(0.0, x));
                        double yc = min(1.0, max(0.0, y));
                        double zc = min(1.0, max(0.0, z));
                        cout << xc << " " << yc << " " << zc << "\n";
                        --remaining;
                    }
                }
            }
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    HCPGenerator gen{n};

    // Binary search for maximal s with count(s) >= n
    double lo = 0.0, hi = 1.0;
    for (int it = 0; it < 70; ++it) {
        double mid = (lo + hi) * 0.5;
        long long c = gen.count_points(mid, n);
        if (c >= n) lo = mid; else hi = mid;
    }
    double s = lo;
    // Safety margin to counter rounding in generation
    for (int t = 0; t < 5; ++t) {
        long long c = gen.count_points(s, n);
        if (c >= n) break;
        s *= 0.999999;
    }

    gen.generate_and_print(s);

    return 0;
}