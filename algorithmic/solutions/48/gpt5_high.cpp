#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if (!(cin >> n)) return 0;

    // Find smallest D such that ceil(D^3 / 2) >= n
    long long D = 1;
    while ((D*D*D + 1) / 2 < n) ++D;

    const double sqrt3 = sqrt(3.0);
    // Slight safety margin to avoid numerical issues near the boundary
    const double eps = 1e-13;
    double h = 1.0 / ( (D - 1) + sqrt3 + eps );
    double r = (sqrt3 * 0.5) * h;

    cout.setf(std::ios::fixed);
    cout << setprecision(12);

    long long printed = 0;
    int parity_target = 0; // Use even parity

    for (long long i = 0; i < D && printed < n; ++i) {
        double x = r + h * i;
        for (long long j = 0; j < D && printed < n; ++j) {
            double y = r + h * j;
            long long start_k = ((i + j) % 2 == parity_target ? 0 : 1);
            for (long long k = start_k; k < D && printed < n; k += 2) {
                double z = r + h * k;
                // Clamp just in case of numerical drift
                if (x < 0) x = 0; if (x > 1) x = 1;
                if (y < 0) y = 0; if (y > 1) y = 1;
                if (z < 0) z = 0; if (z > 1) z = 1;
                cout << x << " " << y << " " << z << "\n";
                ++printed;
            }
        }
    }

    // Fallback (shouldn't be needed, but just in case due to rounding or logic)
    if (printed < n) {
        long long M = D + 1;
        double step = 1.0 / (M + 1);
        double offset = step;
        for (long long i = 0; i < M && printed < n; ++i) {
            double x = offset + step * i;
            for (long long j = 0; j < M && printed < n; ++j) {
                double y = offset + step * j;
                for (long long k = 0; k < M && printed < n; ++k) {
                    double z = offset + step * k;
                    if (x < 0) x = 0; if (x > 1) x = 1;
                    if (y < 0) y = 0; if (y > 1) y = 1;
                    if (z < 0) z = 0; if (z > 1) z = 1;
                    cout << x << " " << y << " " << z << "\n";
                    ++printed;
                }
            }
        }
    }

    return 0;
}