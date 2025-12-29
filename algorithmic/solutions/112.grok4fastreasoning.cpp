#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    cout << fixed << setprecision(10);
    if (n == 2) {
        cout << 2.0 << '\n';
        cout << 0.0 << ' ' << 0.0 << ' ' << 1.0 << '\n';
        cout << 0.0 << ' ' << 0.0 << ' ' << -1.0 << '\n';
        return 0;
    }
    if (n == 3) {
        double rt3 = sqrt(3.0);
        cout << rt3 << '\n';
        cout << 1.0 << ' ' << 0.0 << ' ' << 0.0 << '\n';
        cout << -0.5 << ' ' << rt3 * 0.5 << ' ' << 0.0 << '\n';
        cout << -0.5 << ' ' << -rt3 * 0.5 << ' ' << 0.0 << '\n';
        return 0;
    }
    if (n == 4) {
        double invsqrt3 = 1.0 / sqrt(3.0);
        double md4 = sqrt(8.0 / 3.0);
        cout << md4 << '\n';
        cout << invsqrt3 << ' ' << invsqrt3 << ' ' << invsqrt3 << '\n';
        cout << invsqrt3 << ' ' << -invsqrt3 << ' ' << -invsqrt3 << '\n';
        cout << -invsqrt3 << ' ' << invsqrt3 << ' ' << -invsqrt3 << '\n';
        cout << -invsqrt3 << ' ' << -invsqrt3 << ' ' << invsqrt3 << '\n';
        return 0;
    }
    if (n == 6) {
        double md6 = sqrt(2.0);
        cout << md6 << '\n';
        cout << 0.0 << ' ' << 0.0 << ' ' << 1.0 << '\n';
        cout << 0.0 << ' ' << 0.0 << ' ' << -1.0 << '\n';
        cout << 1.0 << ' ' << 0.0 << ' ' << 0.0 << '\n';
        cout << 0.0 << ' ' << 1.0 << ' ' << 0.0 << '\n';
        cout << -1.0 << ' ' << 0.0 << ' ' << 0.0 << '\n';
        cout << 0.0 << ' ' << -1.0 << ' ' << 0.0 << '\n';
        return 0;
    }
    // Fibonacci spiral for other n
    vector<array<double, 3>> pts(n);
    double alpha = (sqrt(5.0) - 1.0) / 2.0;
    for (int i = 0; i < n; i++) {
        double phi = 2.0 * M_PI * i * alpha;
        double h = 1.0 - 2.0 * (i + 0.5) / n;
        double r = sqrt(1.0 - h * h);
        pts[i][0] = r * cos(phi);
        pts[i][1] = r * sin(phi);
        pts[i][2] = h;
    }
    double min_dist = INFINITY;
    for (int i = 0; i < n; i++) {
        for (int j = i + 1; j < n; j++) {
            double dx = pts[i][0] - pts[j][0];
            double dy = pts[i][1] - pts[j][1];
            double dz = pts[i][2] - pts[j][2];
            double dist = sqrt(dx * dx + dy * dy + dz * dz);
            if (dist < min_dist) min_dist = dist;
        }
    }
    cout << min_dist << '\n';
    for (const auto& p : pts) {
        cout << p[0] << ' ' << p[1] << ' ' << p[2] << '\n';
    }
    return 0;
}