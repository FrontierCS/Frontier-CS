#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    const double PI = acos(-1.0);
    vector<array<double, 3>> pts;
    pts.reserve(n);

    if (n == 2) {
        pts.push_back({0.0, 0.0, 1.0});
        pts.push_back({0.0, 0.0, -1.0});
    } else if (n == 3) {
        for (int i = 0; i < 3; ++i) {
            double phi = 2.0 * PI * i / 3.0;
            double x = cos(phi);
            double y = sin(phi);
            double z = 0.0;
            pts.push_back({x, y, z});
        }
    } else if (n == 4) {
        double inv = 1.0 / sqrt(3.0);
        pts.push_back({ 1.0 * inv,  1.0 * inv,  1.0 * inv});
        pts.push_back({ 1.0 * inv, -1.0 * inv, -1.0 * inv});
        pts.push_back({-1.0 * inv,  1.0 * inv, -1.0 * inv});
        pts.push_back({-1.0 * inv, -1.0 * inv,  1.0 * inv});
    } else {
        const double golden_angle = PI * (3.0 - sqrt(5.0));
        for (int i = 0; i < n; ++i) {
            double k = i + 0.5;
            double z = 1.0 - 2.0 * k / n;
            double r = sqrt(max(0.0, 1.0 - z * z));
            double phi = golden_angle * i;
            double x = r * cos(phi);
            double y = r * sin(phi);
            pts.push_back({x, y, z});
        }
    }

    double min_sq = 1e100;
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            double dx = pts[i][0] - pts[j][0];
            double dy = pts[i][1] - pts[j][1];
            double dz = pts[i][2] - pts[j][2];
            double d2 = dx * dx + dy * dy + dz * dz;
            if (d2 < min_sq) min_sq = d2;
        }
    }

    double min_dist = sqrt(min_sq);

    cout.setf(ios::fixed);
    cout << setprecision(15) << min_dist << '\n';
    for (int i = 0; i < n; ++i) {
        cout << setprecision(15)
             << pts[i][0] << ' ' << pts[i][1] << ' ' << pts[i][2] << '\n';
    }

    return 0;
}