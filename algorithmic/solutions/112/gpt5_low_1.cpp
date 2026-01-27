#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;

    const double PI = acos(-1.0);
    const double phi = (1.0 + sqrt(5.0)) * 0.5;
    const double golden_angle = 2.0 * PI * (1.0 - 1.0 / phi);

    vector<array<double,3>> p(n);
    for (int i = 0; i < n; ++i) {
        double k = i + 0.5;
        double z = 1.0 - 2.0 * k / n;
        double r = sqrt(max(0.0, 1.0 - z * z));
        double theta = golden_angle * i;
        double x = cos(theta) * r;
        double y = sin(theta) * r;
        p[i] = {x, y, z};
    }

    int iters = 15;
    double step_start = 0.03, step_end = 0.005;
    vector<array<double,3>> f(n);

    for (int t = 0; t < iters; ++t) {
        double step = (iters > 1) ? (step_start + (step_end - step_start) * (double)t / (iters - 1)) : step_end;
        for (int i = 0; i < n; ++i) f[i] = {0.0, 0.0, 0.0};
        for (int i = 0; i < n; ++i) {
            const auto &pi = p[i];
            for (int j = i + 1; j < n; ++j) {
                auto &pj = p[j];
                double dx = pi[0] - pj[0];
                double dy = pi[1] - pj[1];
                double dz = pi[2] - pj[2];
                double dist2 = dx*dx + dy*dy + dz*dz + 1e-9;
                double inv2 = 1.0 / dist2;
                double fx = dx * inv2;
                double fy = dy * inv2;
                double fz = dz * inv2;
                f[i][0] += fx; f[i][1] += fy; f[i][2] += fz;
                f[j][0] -= fx; f[j][1] -= fy; f[j][2] -= fz;
            }
        }
        for (int i = 0; i < n; ++i) {
            auto &pi = p[i];
            auto &fi = f[i];
            // Project force onto tangent plane
            double dotfp = fi[0]*pi[0] + fi[1]*pi[1] + fi[2]*pi[2];
            fi[0] -= dotfp * pi[0];
            fi[1] -= dotfp * pi[1];
            fi[2] -= dotfp * pi[2];
            // Limit force magnitude
            double fn = sqrt(fi[0]*fi[0] + fi[1]*fi[1] + fi[2]*fi[2]);
            if (fn > 1.0) {
                fi[0] /= fn; fi[1] /= fn; fi[2] /= fn;
            }
            // Update and renormalize
            pi[0] += step * fi[0];
            pi[1] += step * fi[1];
            pi[2] += step * fi[2];
            double pn = sqrt(pi[0]*pi[0] + pi[1]*pi[1] + pi[2]*pi[2]);
            if (pn > 0) {
                pi[0] /= pn; pi[1] /= pn; pi[2] /= pn;
            } else {
                // fallback to unit vector along z if degenerate
                pi = {0.0, 0.0, 1.0};
            }
        }
    }

    // Compute minimum pairwise distance
    double min_d2 = 1e100;
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            double dx = p[i][0] - p[j][0];
            double dy = p[i][1] - p[j][1];
            double dz = p[i][2] - p[j][2];
            double d2 = dx*dx + dy*dy + dz*dz;
            if (d2 < min_d2) min_d2 = d2;
        }
    }
    double min_dist = sqrt(max(0.0, min_d2));

    cout.setf(std::ios::fixed); 
    cout << setprecision(12) << min_dist << "\n";
    for (int i = 0; i < n; ++i) {
        cout << setprecision(12) << p[i][0] << " " << p[i][1] << " " << p[i][2] << "\n";
    }
    return 0;
}