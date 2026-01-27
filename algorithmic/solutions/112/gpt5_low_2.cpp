#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    const double PI = acos(-1.0);
    vector<array<double,3>> p(n);

    if (n == 2) {
        cout.setf(std::ios::fixed); cout << setprecision(12);
        cout << 2.0 << "\n";
        cout << 0.0 << " " << 0.0 << " " << 1.0 << "\n";
        cout << 0.0 << " " << 0.0 << " " << -1.0 << "\n";
        return 0;
    }

    // Initialize with Fibonacci sphere
    const double golden = (1.0 + sqrt(5.0)) * 0.5;
    for (int i = 0; i < n; ++i) {
        double z = 1.0 - 2.0 * (i + 0.5) / n;
        double r = sqrt(max(0.0, 1.0 - z*z));
        double theta = 2.0 * PI * i / golden;
        double x = cos(theta) * r;
        double y = sin(theta) * r;
        p[i] = {x, y, z};
    }

    // Small random jitter to break symmetry
    std::mt19937_64 rng(712387);
    std::uniform_real_distribution<double> distu(-1e-6, 1e-6);
    for (int i = 0; i < n; ++i) {
        p[i][0] += distu(rng);
        p[i][1] += distu(rng);
        p[i][2] += distu(rng);
        double norm = sqrt(p[i][0]*p[i][0] + p[i][1]*p[i][1] + p[i][2]*p[i][2]);
        for (int k = 0; k < 3; ++k) p[i][k] /= norm;
    }

    int T = 80;
    double c_base = 0.25; // step scaling
    double eps = 1e-9;

    vector<array<double,3>> f(n);

    for (int it = 0; it < T; ++it) {
        // Zero forces
        for (int i = 0; i < n; ++i) f[i] = {0.0, 0.0, 0.0};

        // Compute repulsive forces (Coulomb-like)
        for (int i = 0; i < n; ++i) {
            const auto &pi = p[i];
            for (int j = i+1; j < n; ++j) {
                const auto &pj = p[j];
                double dx = pi[0] - pj[0];
                double dy = pi[1] - pj[1];
                double dz = pi[2] - pj[2];
                double d2 = dx*dx + dy*dy + dz*dz + 1e-12;
                double inv = 1.0 / (d2 * sqrt(d2));
                double fx = dx * inv;
                double fy = dy * inv;
                double fz = dz * inv;
                f[i][0] += fx; f[i][1] += fy; f[i][2] += fz;
                f[j][0] -= fx; f[j][1] -= fy; f[j][2] -= fz;
            }
        }

        // Apply tangential projection and update on the sphere
        double alpha = (c_base / n) * (1.0 - (double)it / T) + (0.02 / n);
        for (int i = 0; i < n; ++i) {
            double px = p[i][0], py = p[i][1], pz = p[i][2];
            double fx = f[i][0], fy = f[i][1], fz = f[i][2];
            // Project force onto tangent plane at p[i]
            double dotpf = px*fx + py*fy + pz*fz;
            fx -= dotpf * px;
            fy -= dotpf * py;
            fz -= dotpf * pz;

            // Limit step to avoid overshoot
            double fnorm = sqrt(fx*fx + fy*fy + fz*fz) + eps;
            double step = alpha;
            double max_step = 0.05; // radians approx
            if (step * fnorm > max_step) step = max_step / fnorm;

            p[i][0] = px + step * fx;
            p[i][1] = py + step * fy;
            p[i][2] = pz + step * fz;

            double norm = sqrt(p[i][0]*p[i][0] + p[i][1]*p[i][1] + p[i][2]*p[i][2]);
            p[i][0] /= norm; p[i][1] /= norm; p[i][2] /= norm;
        }
    }

    // Compute min pairwise distance
    double min_d = 1e100;
    for (int i = 0; i < n; ++i) {
        for (int j = i+1; j < n; ++j) {
            double dx = p[i][0] - p[j][0];
            double dy = p[i][1] - p[j][1];
            double dz = p[i][2] - p[j][2];
            double d = sqrt(dx*dx + dy*dy + dz*dz);
            if (d < min_d) min_d = d;
        }
    }

    cout.setf(std::ios::fixed); cout << setprecision(12);
    cout << min_d << "\n";
    for (int i = 0; i < n; ++i) {
        cout << p[i][0] << " " << p[i][1] << " " << p[i][2] << "\n";
    }

    return 0;
}