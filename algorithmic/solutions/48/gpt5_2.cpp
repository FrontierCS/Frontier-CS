#include <bits/stdc++.h>
using namespace std;

static inline long long ceil_div(long long a, long long b) {
    return (a + b - 1) / b;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long n;
    if (!(cin >> n)) return 0;

    const double sqrt2 = sqrt(2.0);
    long long Ptarget = 2LL * n - 1;
    if (Ptarget < 1) Ptarget = 1;

    int m0 = (int)ceil(pow((long double)Ptarget, 1.0L / 3.0L));
    int low = 1;
    int high = max(2, m0 + 30); // generous search window

    double bestR = -1.0;
    int bestNx = 1, bestNy = 1, bestNz = 1;

    for (int Nx = low; Nx <= high; ++Nx) {
        for (int Ny = low; Ny <= high; ++Ny) {
            long long xy = 1LL * Nx * Ny;
            if (xy <= 0) continue; // overflow guard (won't happen here)
            int Nz = (int)ceil_div(Ptarget, xy);
            if (Nz < 1) Nz = 1;

            double sX = 1.0 / ( (Nx - 1) + sqrt2 );
            double sY = 1.0 / ( (Ny - 1) + sqrt2 );
            double sZ = 1.0 / ( (Nz - 1) + sqrt2 );
            double s = min(sX, min(sY, sZ));
            double r = s / sqrt2;

            // Ensure capacity
            long long P = 1LL * Nx * Ny * Nz;
            long long M = (P + 1) / 2; // ceil(P/2)
            if (M < n) continue;

            // Choose best by maximizing r; tie-break by smaller P, then by smaller sum of Ni
            if (r > bestR + 1e-15) {
                bestR = r;
                bestNx = Nx; bestNy = Ny; bestNz = Nz;
            } else if (fabs(r - bestR) <= 1e-15) {
                long long bestP = 1LL * bestNx * bestNy * bestNz;
                if (P < bestP || (P == bestP && (Nx + Ny + Nz) < (bestNx + bestNy + bestNz))) {
                    bestR = r;
                    bestNx = Nx; bestNy = Ny; bestNz = Nz;
                }
            }
        }
    }

    int Nx = bestNx, Ny = bestNy, Nz = bestNz;
    double sX = 1.0 / ( (Nx - 1) + sqrt2 );
    double sY = 1.0 / ( (Ny - 1) + sqrt2 );
    double sZ = 1.0 / ( (Nz - 1) + sqrt2 );
    double s = min(sX, min(sY, sZ));

    double ox = (1.0 - (Nx - 1) * s) / 2.0;
    double oy = (1.0 - (Ny - 1) * s) / 2.0;
    double oz = (1.0 - (Nz - 1) * s) / 2.0;

    cout.setf(ios::fixed);
    cout << setprecision(15);

    long long printed = 0;
    for (int i = 0; i < Nx && printed < n; ++i) {
        double x = ox + i * s;
        for (int j = 0; j < Ny && printed < n; ++j) {
            double y = oy + j * s;
            int kstart = ((i + j) & 1) ? 1 : 0;
            for (int k = kstart; k < Nz && printed < n; k += 2) {
                double z = oz + k * s;
                // Clamp to [0,1] for safety against roundoff
                double xc = min(1.0, max(0.0, x));
                double yc = min(1.0, max(0.0, y));
                double zc = min(1.0, max(0.0, z));
                cout << xc << " " << yc << " " << zc << "\n";
                ++printed;
            }
        }
    }

    // Fallback (shouldn't happen, but just in case): fill remaining with center points
    while (printed < n) {
        cout << "0.5 0.5 0.5\n";
        ++printed;
    }

    return 0;
}