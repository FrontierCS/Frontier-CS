#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long n;
    if (!(cin >> n)) return 0;

    const double sqrt2 = sqrt(2.0);

    // Search FCC lattice parameters
    int bestNx = 0, bestNy = 0, bestNz = 0;
    double best_r = -1.0;

    // Reasonable upper bound for grid counts (sufficient for n <= 4096)
    int Mmax = 64;

    for (int Nx = 1; Nx <= Mmax; ++Nx) {
        for (int Ny = 1; Ny <= Mmax; ++Ny) {
            for (int Nz = 1; Nz <= Mmax; ++Nz) {
                long long total = 1LL * Nx * Ny * Nz;
                long long cnt = total / 2;
                if ((Nx % 2 == 1) && (Ny % 2 == 1) && (Nz % 2 == 1)) cnt = (total + 1) / 2;
                if (cnt < n) continue;
                int M = max(Nx, max(Ny, Nz));
                double h = 1.0 / ( (double)(M - 1) + sqrt2 );
                double r = h * sqrt2 * 0.5;
                if (r > best_r) {
                    best_r = r;
                    bestNx = Nx; bestNy = Ny; bestNz = Nz;
                }
            }
        }
    }

    vector<array<double,3>> pts;
    pts.reserve((size_t)min<long long>(n, 1000000));

    if (best_r > 0) {
        int Nx = bestNx, Ny = bestNy, Nz = bestNz;
        int M = max(Nx, max(Ny, Nz));
        double h = 1.0 / ( (double)(M - 1) + sqrt2 );
        double o = h * sqrt2 * 0.5; // margin so boundary distance equals r
        // Generate FCC points (i+j+k even)
        for (int i = 0; i < Nx && (long long)pts.size() < n; ++i) {
            double x = o + i * h;
            for (int j = 0; j < Ny && (long long)pts.size() < n; ++j) {
                double y = o + j * h;
                for (int k = 0; k < Nz && (long long)pts.size() < n; ++k) {
                    if (((i + j + k) & 1) != 0) continue;
                    double z = o + k * h;
                    if (x < -1e-12 || x > 1.0 + 1e-12) continue;
                    if (y < -1e-12 || y > 1.0 + 1e-12) continue;
                    if (z < -1e-12 || z > 1.0 + 1e-12) continue;
                    pts.push_back({x, y, z});
                    if ((long long)pts.size() == n) break;
                }
            }
        }
    }

    // Fallback to simple cubic grid if needed
    if ((long long)pts.size() < n) {
        pts.clear();
        // Choose m x k x l grid (balanced cube)
        int m = max(1, (int)round(cbrt((double)n)));
        while (1LL * m * m * m < n) ++m;
        int M = m;
        // Place points at centers of M^3 cells
        for (int i = 0; (long long)pts.size() < n && i < M; ++i) {
            double x = (i + 0.5) / M;
            for (int j = 0; (long long)pts.size() < n && j < M; ++j) {
                double y = (j + 0.5) / M;
                for (int k = 0; (long long)pts.size() < n && k < M; ++k) {
                    double z = (k + 0.5) / M;
                    pts.push_back({x, y, z});
                    if ((long long)pts.size() == n) break;
                }
            }
        }
    }

    cout.setf(std::ios::fixed); 
    cout << setprecision(12);
    for (size_t i = 0; i < (size_t)n; ++i) {
        auto p = pts[i];
        // Clamp to [0,1] in case of tiny numerical drift
        double x = min(1.0, max(0.0, p[0]));
        double y = min(1.0, max(0.0, p[1]));
        double z = min(1.0, max(0.0, p[2]));
        cout << x << " " << y << " " << z << "\n";
    }

    return 0;
}