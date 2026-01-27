#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<array<double, 3>> p(n);

    const double PI = acos(-1.0);

    if (n == 1) {
        p[0] = {0.0, 0.0, 0.0};
    } else if (n == 2) {
        p[0] = {0.0, 0.0, 1.0};
        p[1] = {0.0, 0.0, -1.0};
    } else if (n == 3) {
        for (int i = 0; i < 3; ++i) {
            double theta = 2.0 * PI * i / 3.0;
            double x = cos(theta);
            double y = sin(theta);
            double z = 0.0;
            p[i] = {x, y, z};
        }
    } else if (n == 4) {
        double s = 1.0 / sqrt(3.0);
        p[0] = { s,  s,  s};
        p[1] = { s, -s, -s};
        p[2] = {-s,  s, -s};
        p[3] = {-s, -s,  s};
    } else {
        double phi = PI * (3.0 - sqrt(5.0)); // golden angle in radians
        for (int i = 0; i < n; ++i) {
            double y = 1.0 - (2.0 * i) / (n - 1.0);
            double radius = sqrt(max(0.0, 1.0 - y * y));
            double theta = phi * i;
            double x = cos(theta) * radius;
            double z = sin(theta) * radius;
            p[i] = {x, y, z};
        }
    }

    double min_d2 = 1e100;
    if (n >= 2) {
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                double dx = p[i][0] - p[j][0];
                double dy = p[i][1] - p[j][1];
                double dz = p[i][2] - p[j][2];
                double d2 = dx * dx + dy * dy + dz * dz;
                if (d2 < min_d2) min_d2 = d2;
            }
        }
    }

    double minDist = (n >= 2) ? sqrt(min_d2) : 0.0;

    cout.setf(ios::fixed);
    cout << setprecision(12) << minDist << "\n";
    for (int i = 0; i < n; ++i) {
        cout << setprecision(12)
             << p[i][0] << " " << p[i][1] << " " << p[i][2] << "\n";
    }

    return 0;
}