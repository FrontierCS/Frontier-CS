#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    const double PI = acos(-1.0);
    const double golden_angle = PI * (3.0 - sqrt(5.0));

    vector<array<double, 3>> p(n);

    // Initial placement: spherical Fibonacci lattice on the unit sphere
    for (int i = 0; i < n; ++i) {
        double z = 1.0 - 2.0 * ((i + 0.5) / (double)n);
        double r = sqrt(max(0.0, 1.0 - z * z));
        double phi = golden_angle * i;
        double x = cos(phi) * r;
        double y = sin(phi) * r;
        p[i] = {x, y, z};
    }

    if (n > 1) {
        // Repulsion-based refinement on the sphere
        long long pairs = 1LL * n * (n - 1) / 2;
        long long iter = 0;
        if (pairs > 0) iter = 10000000LL / max(1LL, pairs);
        if (iter < 1) iter = 1;
        if (iter > 30000) iter = 30000;

        double step = 0.2 / n;
        vector<array<double, 3>> f(n);

        for (long long it = 0; it < iter; ++it) {
            for (int i = 0; i < n; ++i) {
                f[i][0] = f[i][1] = f[i][2] = 0.0;
            }

            for (int i = 0; i < n; ++i) {
                for (int j = i + 1; j < n; ++j) {
                    double dx = p[i][0] - p[j][0];
                    double dy = p[i][1] - p[j][1];
                    double dz = p[i][2] - p[j][2];
                    double d2 = dx * dx + dy * dy + dz * dz;
                    if (d2 < 1e-6) d2 = 1e-6;
                    double inv = 1.0 / d2;
                    double fx = dx * inv;
                    double fy = dy * inv;
                    double fz = dz * inv;
                    f[i][0] += fx;
                    f[i][1] += fy;
                    f[i][2] += fz;
                    f[j][0] -= fx;
                    f[j][1] -= fy;
                    f[j][2] -= fz;
                }
            }

            for (int i = 0; i < n; ++i) {
                p[i][0] += step * f[i][0];
                p[i][1] += step * f[i][1];
                p[i][2] += step * f[i][2];
                double norm = sqrt(p[i][0] * p[i][0] + p[i][1] * p[i][1] + p[i][2] * p[i][2]);
                if (norm > 0.0) {
                    p[i][0] /= norm;
                    p[i][1] /= norm;
                    p[i][2] /= norm;
                } else {
                    p[i][0] = 1.0;
                    p[i][1] = 0.0;
                    p[i][2] = 0.0;
                }
            }

            step *= 0.99;
        }
    }

    // Compute minimum pairwise distance
    double min_d2 = 1e300;
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            double dx = p[i][0] - p[j][0];
            double dy = p[i][1] - p[j][1];
            double dz = p[i][2] - p[j][2];
            double d2 = dx * dx + dy * dy + dz * dz;
            if (d2 < min_d2) min_d2 = d2;
        }
    }

    double min_dist = sqrt(min_d2);

    cout.setf(ios::fixed);
    cout << setprecision(10) << min_dist << '\n';
    for (int i = 0; i < n; ++i) {
        cout << setprecision(10)
             << p[i][0] << ' ' << p[i][1] << ' ' << p[i][2] << '\n';
    }

    return 0;
}