#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    const double PI = acos(-1.0);
    const double golden_angle = PI * (3.0 - sqrt(5.0)); // ~2.399963
    
    vector<array<double,3>> pts(n);
    if (n == 2) {
        pts[0] = {0.0, 0.0, 1.0};
        pts[1] = {0.0, 0.0, -1.0};
    } else {
        for (int k = 0; k < n; ++k) {
            double z = 1.0 - 2.0 * ( (k + 0.5) / n );
            double r = sqrt(max(0.0, 1.0 - z*z));
            double theta = golden_angle * k;
            double x = cos(theta) * r;
            double y = sin(theta) * r;
            pts[k] = {x, y, z};
        }
    }

    // Compute minimum pairwise distance
    double min_d2 = numeric_limits<double>::infinity();
    for (int i = 0; i < n; ++i) {
        const auto &a = pts[i];
        for (int j = i + 1; j < n; ++j) {
            const auto &b = pts[j];
            double dx = a[0] - b[0];
            double dy = a[1] - b[1];
            double dz = a[2] - b[2];
            double d2 = dx*dx + dy*dy + dz*dz;
            if (d2 < min_d2) min_d2 = d2;
        }
    }
    double min_dist = sqrt(min_d2);

    cout.setf(std::ios::fixed); 
    cout << setprecision(12) << min_dist << "\n";
    cout << setprecision(17);
    for (int i = 0; i < n; ++i) {
        cout << pts[i][0] << " " << pts[i][1] << " " << pts[i][2] << "\n";
    }
    return 0;
}