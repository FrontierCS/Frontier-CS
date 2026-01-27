#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    const double PI = acos(-1.0);
    const double golden_angle = PI * (3.0 - sqrt(5.0));
    const double R = 1.0 - 1e-12;

    vector<array<double, 3>> pts;
    pts.reserve(n);

    auto add = [&](double x, double y, double z) {
        pts.push_back({x, y, z});
    };

    bool special = false;
    if (n == 2) {
        special = true;
        add(0.0, 0.0, R);
        add(0.0, 0.0, -R);
    } else if (n == 3) {
        special = true;
        for (int k = 0; k < 3; ++k) {
            double ang = 2.0 * PI * k / 3.0;
            add(R * cos(ang), R * sin(ang), 0.0);
        }
    } else if (n == 4) {
        special = true;
        double s = R / sqrt(3.0);
        add( s,  s,  s);
        add(-s, -s,  s);
        add(-s,  s, -s);
        add( s, -s, -s);
    } else if (n == 5) {
        special = true;
        add(0.0, 0.0, R);
        add(0.0, 0.0, -R);
        for (int k = 0; k < 3; ++k) {
            double ang = 2.0 * PI * k / 3.0;
            add(R * cos(ang), R * sin(ang), 0.0);
        }
    } else if (n == 6) {
        special = true;
        add( R, 0.0, 0.0);
        add(-R, 0.0, 0.0);
        add(0.0,  R, 0.0);
        add(0.0, -R, 0.0);
        add(0.0, 0.0,  R);
        add(0.0, 0.0, -R);
    } else if (n == 8) {
        special = true;
        double s = R / sqrt(3.0);
        for (int sx : {-1, 1}) {
            for (int sy : {-1, 1}) {
                for (int sz : {-1, 1}) {
                    add(sx * s, sy * s, sz * s);
                }
            }
        }
    }

    if (!special) {
        for (int i = 0; i < n; ++i) {
            double z = 1.0 - 2.0 * (i + 0.5) / n;
            double r = sqrt(max(0.0, 1.0 - z * z));
            double phi = golden_angle * i;
            double x = r * cos(phi);
            double y = r * sin(phi);
            add(R * x, R * y, R * z);
        }
    }

    // Compute minimum pairwise distance
    double min_d2 = numeric_limits<double>::infinity();
    for (int i = 0; i < n; ++i) {
        auto &a = pts[i];
        for (int j = i + 1; j < n; ++j) {
            auto &b = pts[j];
            double dx = a[0] - b[0];
            double dy = a[1] - b[1];
            double dz = a[2] - b[2];
            double d2 = dx*dx + dy*dy + dz*dz;
            if (d2 < min_d2) min_d2 = d2;
        }
    }
    double min_dist = (min_d2 < numeric_limits<double>::infinity() ? sqrt(min_d2) : 0.0);

    cout.setf(std::ios::fixed); 
    cout << setprecision(15) << min_dist << "\n";
    for (int i = 0; i < n; ++i) {
        cout << setprecision(15) << pts[i][0] << " " << pts[i][1] << " " << pts[i][2] << "\n";
    }

    return 0;
}