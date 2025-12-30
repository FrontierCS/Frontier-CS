#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<array<double, 3>> points(n);
    double pi = acos(-1.0);
    if (n == 2) {
        points[0] = {0.0, 0.0, 1.0};
        points[1] = {0.0, 0.0, -1.0};
    } else if (n == 3) {
        double s = sqrt(3.0) / 2.0;
        points[0] = {1.0, 0.0, 0.0};
        points[1] = {-0.5, s, 0.0};
        points[2] = {-0.5, -s, 0.0};
    } else if (n == 4) {
        double t = 1.0 / sqrt(3.0);
        points[0] = {t, t, t};
        points[1] = {t, -t, -t};
        points[2] = {-t, t, -t};
        points[3] = {-t, -t, t};
    } else {
        double golden = (1.0 + sqrt(5.0)) / 2.0;
        for (int i = 0; i < n; i++) {
            double zi = -1.0 + 2.0 * (static_cast<double>(i) + 0.5) / n;
            double ph = 2.0 * pi * static_cast<double>(i) / golden;
            double r = sqrt(1.0 - zi * zi);
            points[i][0] = r * cos(ph);
            points[i][1] = r * sin(ph);
            points[i][2] = zi;
        }
    }
    // Compute min dist
    double mind = 1e100;
    for (int i = 0; i < n; i++) {
        for (int j = i + 1; j < n; j++) {
            double dx = points[i][0] - points[j][0];
            double dy = points[i][1] - points[j][1];
            double dz = points[i][2] - points[j][2];
            double d = sqrt(dx * dx + dy * dy + dz * dz);
            if (d < mind) mind = d;
        }
    }
    cout << fixed << setprecision(10) << mind << endl;
    for (auto& p : points) {
        cout << fixed << setprecision(10) << p[0] << " " << p[1] << " " << p[2] << endl;
    }
    return 0;
}