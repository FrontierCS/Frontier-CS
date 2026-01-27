#include <bits/stdc++.h>
using namespace std;

struct Vec3 {
    double x, y, z;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<Vec3> p(n);
    const double PI = acos(-1.0);
    const double goldenAngle = PI * (3.0 - sqrt(5.0));

    if (n == 1) {
        p[0] = {0.0, 0.0, 1.0};
        cout.setf(ios::fixed);
        cout << setprecision(15) << 0.0 << "\n";
        cout << setprecision(15) << p[0].x << " " << p[0].y << " " << p[0].z << "\n";
        return 0;
    }

    // Initial placement using Fibonacci sphere
    for (int i = 0; i < n; ++i) {
        double y = 1.0 - 2.0 * i / double(n - 1);
        double r = sqrt(max(0.0, 1.0 - y * y));
        double phi = goldenAngle * i;
        double x = r * cos(phi);
        double z = r * sin(phi);
        double len2 = x * x + y * y + z * z;
        double invLen = 1.0 / sqrt(len2);
        p[i] = {x * invLen, y * invLen, z * invLen};
    }

    // Repulsion-based refinement
    int maxIter;
    if (n <= 50) maxIter = 80;
    else if (n <= 200) maxIter = 60;
    else if (n <= 400) maxIter = 45;
    else if (n <= 800) maxIter = 35;
    else maxIter = 30;

    double step0 = 0.15;
    vector<Vec3> F(n);
    double invN = 1.0 / n;
    const double eps = 1e-12;

    for (int iter = 0; iter < maxIter; ++iter) {
        // Zero forces
        for (int i = 0; i < n; ++i) {
            F[i].x = F[i].y = F[i].z = 0.0;
        }

        // Accumulate repulsive forces
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                double dx = p[i].x - p[j].x;
                double dy = p[i].y - p[j].y;
                double dz = p[i].z - p[j].z;
                double dist2 = dx * dx + dy * dy + dz * dz + eps;
                double inv = 1.0 / dist2;
                double fx = dx * inv;
                double fy = dy * inv;
                double fz = dz * inv;
                F[i].x += fx; F[i].y += fy; F[i].z += fz;
                F[j].x -= fx; F[j].y -= fy; F[j].z -= fz;
            }
        }

        double step = step0 * (1.0 - double(iter) / maxIter);

        // Update positions and renormalize to the sphere
        for (int i = 0; i < n; ++i) {
            double fx = F[i].x * invN;
            double fy = F[i].y * invN;
            double fz = F[i].z * invN;
            double nx = p[i].x + fx * step;
            double ny = p[i].y + fy * step;
            double nz = p[i].z + fz * step;
            double len2 = nx * nx + ny * ny + nz * nz;
            if (len2 > 0.0) {
                double invLen = 1.0 / sqrt(len2);
                p[i].x = nx * invLen;
                p[i].y = ny * invLen;
                p[i].z = nz * invLen;
            }
        }
    }

    // Compute minimal pairwise distance
    double min_d2 = 1e300;
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            double dx = p[i].x - p[j].x;
            double dy = p[i].y - p[j].y;
            double dz = p[i].z - p[j].z;
            double d2 = dx * dx + dy * dy + dz * dz;
            if (d2 < min_d2) min_d2 = d2;
        }
    }
    double min_dist = sqrt(min_d2);

    cout.setf(ios::fixed);
    cout << setprecision(15) << min_dist << "\n";
    for (int i = 0; i < n; ++i) {
        cout << setprecision(15) << p[i].x << " " << p[i].y << " " << p[i].z << "\n";
    }

    return 0;
}