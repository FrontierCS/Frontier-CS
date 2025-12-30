#include <iostream>
#include <vector>
#include <array>
#include <cmath>
#include <iomanip>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;
    if (n <= 0) return 0;

    // Simple cubic (SC) baseline grid
    int M_sc = 1;
    while (1LL * M_sc * M_sc * M_sc < n) ++M_sc;
    double r_sc = 1.0 / (2.0 * M_sc);

    // FCC candidate
    const double d0_fcc = std::sqrt(0.5); // minimal distance in unscaled FCC

    int Nx = 1;
    while (4LL * Nx * Nx * Nx < n) ++Nx;

    vector<array<double,3>> pts;
    pts.reserve((size_t)n);

    double minx = 1e100, miny = 1e100, minz = 1e100;
    double maxx = -1e100, maxy = -1e100, maxz = -1e100;

    const double off[4][3] = {
        {0.0, 0.0, 0.0},
        {0.0, 0.5, 0.5},
        {0.5, 0.0, 0.5},
        {0.5, 0.5, 0.0}
    };

    bool done = false;
    for (int k = 0; k < Nx && !done; ++k) {
        for (int j = 0; j < Nx && !done; ++j) {
            for (int i = 0; i < Nx; ++i) {
                for (int t = 0; t < 4; ++t) {
                    if ((long long)pts.size() >= n) {
                        done = true;
                        break;
                    }
                    double x = i + off[t][0];
                    double y = j + off[t][1];
                    double z = k + off[t][2];
                    pts.push_back({x, y, z});
                    if (x < minx) minx = x;
                    if (x > maxx) maxx = x;
                    if (y < miny) miny = y;
                    if (y > maxy) maxy = y;
                    if (z < minz) minz = z;
                    if (z > maxz) maxz = z;
                }
                if (done) break;
            }
        }
    }

    double Sx = maxx - minx;
    double Sy = maxy - miny;
    double Sz = maxz - minz;
    double S = Sx;
    if (Sy > S) S = Sy;
    if (Sz > S) S = Sz;

    double alpha_fcc = 1.0 / (S + d0_fcc);
    double r_fcc = 0.5 * alpha_fcc * d0_fcc;

    cout.setf(ios::fixed);
    cout << setprecision(10);

    if (r_fcc >= r_sc) {
        // Use FCC packing
        const double EPS = 1e-12;
        for (const auto &p : pts) {
            double x = alpha_fcc * (p[0] - minx) + r_fcc;
            double y = alpha_fcc * (p[1] - miny) + r_fcc;
            double z = alpha_fcc * (p[2] - minz) + r_fcc;

            if (x < 0.0 && x > -EPS) x = 0.0;
            if (y < 0.0 && y > -EPS) y = 0.0;
            if (z < 0.0 && z > -EPS) z = 0.0;
            if (x > 1.0 && x < 1.0 + EPS) x = 1.0;
            if (y > 1.0 && y < 1.0 + EPS) y = 1.0;
            if (z > 1.0 && z < 1.0 + EPS) z = 1.0;

            cout << x << ' ' << y << ' ' << z << '\n';
        }
    } else {
        // Use simple cubic grid packing
        long long count = 0;
        for (int k = 0; k < M_sc && count < n; ++k) {
            for (int j = 0; j < M_sc && count < n; ++j) {
                for (int i = 0; i < M_sc && count < n; ++i) {
                    double x = (i + 0.5) / (double)M_sc;
                    double y = (j + 0.5) / (double)M_sc;
                    double z = (k + 0.5) / (double)M_sc;
                    cout << x << ' ' << y << ' ' << z << '\n';
                    ++count;
                }
            }
        }
    }

    return 0;
}