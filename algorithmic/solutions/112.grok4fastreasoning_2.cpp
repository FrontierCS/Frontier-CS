#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<array<double, 3>> points;
    double min_dist;
    const double PI = acos(-1.0);
    const double golden = (1.0 + sqrt(5.0)) / 2.0;
    if (n == 2) {
        min_dist = 2.0;
        points = {{{0,0,1}}, {{0,0,-1}}};
    } else if (n == 3) {
        min_dist = sqrt(3.0);
        double s = sqrt(3.0) / 2.0;
        points = {{{1.0, 0.0, 0.0}},
                  {{-0.5, s, 0.0}},
                  {{-0.5, -s, 0.0}}};
    } else if (n == 4) {
        min_dist = sqrt(8.0 / 3.0);
        double norm = sqrt(3.0);
        points = {{{1,1,1}},
                  {{1,-1,-1}},
                  {{-1,1,-1}},
                  {{-1,-1,1}}};
        for (auto& p : points) {
            p[0] /= norm;
            p[1] /= norm;
            p[2] /= norm;
        }
    } else if (n == 6) {
        min_dist = sqrt(2.0);
        points = {{{1,0,0}},
                  {{-1,0,0}},
                  {{0,1,0}},
                  {{0,-1,0}},
                  {{0,0,1}},
                  {{0,0,-1}}};
    } else {
        points.resize(n);
        for (int i = 0; i < n; ++i) {
            double zi = -1.0 + 2.0 * (i + 0.5) / n;
            double phii = 2.0 * PI * i / golden;
            double r = sqrt(1.0 - zi * zi);
            double x = r * cos(phii);
            double y = r * sin(phii);
            points[i] = {x, y, zi};
        }
        min_dist = 1e9;
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                double dx = points[i][0] - points[j][0];
                double dy = points[i][1] - points[j][1];
                double dz = points[i][2] - points[j][2];
                double d = sqrt(dx*dx + dy*dy + dz*dz);
                if (d < min_dist) min_dist = d;
            }
        }
    }
    cout << fixed << setprecision(10) << min_dist << endl;
    for (const auto& p : points) {
        cout << fixed << setprecision(10) << p[0] << " " << p[1] << " " << p[2] << endl;
    }
    return 0;
}