#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long n;
    if (!(cin >> n)) return 0;

    // Search for best FCC lattice grid dimensions (Nx, Ny, Nz)
    // Points are integer grid with (i+j+k)%2==0, scaled and shifted into [0,1]^3
    // Axis step = t, boundary margin r = (sqrt(2)/2)*t, so constraints:
    // t <= 1 / (Ni - 1 + sqrt(2)) for each i in {x,y,z}
    // Count M = number of even-parity points in the box
    const double SQRT2 = std::sqrt(2.0);

    auto count_even_parity = [](long long Nx, long long Ny, long long Nz) -> long long {
        long long prod = Nx * Ny * Nz;
        if ((Nx % 2 == 0) || (Ny % 2 == 0) || (Nz % 2 == 0)) {
            return prod / 2;
        } else {
            return (prod + 1) / 2;
        }
    };

    // Initial guess for balanced grid
    long double target = 2.0L * (long double)n;
    long long N0 = (long long)ceill(powl(target, 1.0L/3.0L));

    // Reasonable search window around N0
    long long low = (N0 > 6 ? N0 - 6 : 1);
    long long high = N0 + 6;

    double best_t = -1.0;
    long long bestNx = 0, bestNy = 0, bestNz = 0;
    long long bestM = 0;

    for (long long Nx = low; Nx <= high; ++Nx) {
        for (long long Ny = low; Ny <= high; ++Ny) {
            for (long long Nz = low; Nz <= high; ++Nz) {
                long long M = count_even_parity(Nx, Ny, Nz);
                if (M < n) continue;
                double tx = 1.0 / ( (double)(Nx - 1) + SQRT2 );
                double ty = 1.0 / ( (double)(Ny - 1) + SQRT2 );
                double tz = 1.0 / ( (double)(Nz - 1) + SQRT2 );
                double t = min(tx, min(ty, tz));
                if (t > best_t - 1e-18) {
                    if (t > best_t + 1e-18 || M < bestM || bestM == 0) {
                        best_t = t;
                        bestNx = Nx; bestNy = Ny; bestNz = Nz;
                        bestM = M;
                    }
                }
            }
        }
    }

    if (best_t < 0) {
        // Fallback: simple cubic grid (baseline) if something went wrong
        // Choose m=k=l minimal such that m*k*l >= n
        long long m = ceil(cbrt((double)n));
        while ((long long)m*m*m < n) ++m;
        double r = 1.0 / (2.0 * m);
        cout.setf(std::ios::fixed); cout<<setprecision(10);
        long long cnt = 0;
        for (long long i=0;i<m && cnt<n;i++){
            for (long long j=0;j<m && cnt<n;j++){
                for (long long k=0;k<m && cnt<n;k++){
                    double x = r + (double)i*(1.0-2.0*r)/(m-1==0?1:m-1);
                    double y = r + (double)j*(1.0-2.0*r)/(m-1==0?1:m-1);
                    double z = r + (double)k*(1.0-2.0*r)/(m-1==0?1:m-1);
                    cout << x << " " << y << " " << z << "\n";
                    cnt++;
                }
            }
        }
        return 0;
    }

    double t = best_t;
    double r = 0.5 * SQRT2 * t;

    // Generate points
    cout.setf(std::ios::fixed);
    cout << setprecision(10);

    long long emitted = 0;
    for (long long i = 0; i < bestNx && emitted < n; ++i) {
        double x = r + i * t;
        for (long long j = 0; j < bestNy && emitted < n; ++j) {
            double y = r + j * t;
            for (long long k = 0; k < bestNz && emitted < n; ++k) {
                if ( ((i + j + k) & 1) != 0 ) continue;
                double z = r + k * t;
                // Ensure within [0,1] numerically (should be by construction)
                if (x < -1e-12 || x > 1+1e-12 ||
                    y < -1e-12 || y > 1+1e-12 ||
                    z < -1e-12 || z > 1+1e-12) continue;
                cout << x << " " << y << " " << z << "\n";
                emitted++;
                if (emitted >= n) break;
            }
        }
    }

    // Safety: if not enough due to unexpected issues, fill with random inside cube
    if (emitted < n) {
        std::mt19937_64 rng(1234567);
        std::uniform_real_distribution<double> U(0.0, 1.0);
        while (emitted < n) {
            double x = U(rng);
            double y = U(rng);
            double z = U(rng);
            cout << x << " " << y << " " << z << "\n";
            emitted++;
        }
    }
    return 0;
}