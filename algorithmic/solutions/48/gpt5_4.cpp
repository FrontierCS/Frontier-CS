#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if (!(cin >> n)) return 0;

    // Simple Cubic (SC) candidate
    auto ceil_cuberoot = [](long long x) -> long long {
        long long a = 1;
        while (a * a * a < x) ++a;
        return a;
    };
    long long S = ceil_cuberoot(n);
    long double r_sc = 1.0L / (2.0L * S);
    long double s_sc = 1.0L / S; // step along each axis
    long double start_sc = (1.0L - (S - 1) * s_sc) / 2.0L; // equals r_sc

    // Face-Centered Cubic (FCC) candidate
    auto max_fcc_points = [](long long L) -> long long {
        // Number of lattice points with i+j+k even in [0..L-1]^3
        // If L is odd: (L^3 + 1)/2, else L^3/2
        long long L3 = L * L * L;
        if (L & 1) return (L3 + 1) / 2;
        return L3 / 2;
    };
    long long L = 1;
    while (max_fcc_points(L) < n) ++L;
    long double sqrt2 = sqrtl(2.0L);
    long double r_fcc = 1.0L / (2.0L + sqrt2 * (L - 1)); // optimal radius for given L
    long double s_fcc = sqrt2 * r_fcc;                   // step along each axis
    long double start_fcc = (1.0L - (L - 1) * s_fcc) / 2.0L; // equals r_fcc

    bool use_fcc = (r_fcc > r_sc);

    cout.setf(std::ios::fmtflags(0), std::ios::floatfield);
    cout << setprecision(17);

    long long printed = 0;

    if (use_fcc) {
        int Li = (int)L;
        for (int i = 0; i < Li && printed < n; ++i) {
            long double x = start_fcc + (long double)i * s_fcc;
            for (int j = 0; j < Li && printed < n; ++j) {
                long double y = start_fcc + (long double)j * s_fcc;
                int kstart = ((i + j) & 1) ? 1 : 0;
                for (int k = kstart; k < Li && printed < n; k += 2) {
                    long double z = start_fcc + (long double)k * s_fcc;
                    double xd = (double)x, yd = (double)y, zd = (double)z;
                    if (xd < 0) xd = 0; if (yd < 0) yd = 0; if (zd < 0) zd = 0;
                    if (xd > 1) xd = 1; if (yd > 1) yd = 1; if (zd > 1) zd = 1;
                    cout << xd << ' ' << yd << ' ' << zd << '\n';
                    ++printed;
                }
            }
        }
    } else {
        int Si = (int)S;
        for (int i = 0; i < Si && printed < n; ++i) {
            long double x = start_sc + (long double)i * s_sc;
            for (int j = 0; j < Si && printed < n; ++j) {
                long double y = start_sc + (long double)j * s_sc;
                for (int k = 0; k < Si && printed < n; ++k) {
                    long double z = start_sc + (long double)k * s_sc;
                    double xd = (double)x, yd = (double)y, zd = (double)z;
                    if (xd < 0) xd = 0; if (yd < 0) yd = 0; if (zd < 0) zd = 0;
                    if (xd > 1) xd = 1; if (yd > 1) yd = 1; if (zd > 1) zd = 1;
                    cout << xd << ' ' << yd << ' ' << zd << '\n';
                    ++printed;
                }
            }
        }
    }

    return 0;
}