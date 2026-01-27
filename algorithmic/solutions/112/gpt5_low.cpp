#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    const long double PI = acosl(-1.0L);
    const long double golden_angle = PI * (3.0L - sqrtl(5.0L)); // ~2.399963...

    vector<array<long double,3>> pts;
    pts.reserve(n);

    for (int k = 0; k < n; ++k) {
        long double z = 1.0L - 2.0L * ( (k + 0.5L) / (long double)n );
        long double r = sqrtl(max(0.0L, 1.0L - z*z));
        long double phi = golden_angle * k;
        long double x = r * cosl(phi);
        long double y = r * sinl(phi);
        long double norm = sqrtl(x*x + y*y + z*z);
        // Normalize to unit sphere to avoid tiny drift
        if (norm > 0) {
            x /= norm; y /= norm; z /= norm;
        }
        pts.push_back({x,y,z});
    }

    long double min_d2 = numeric_limits<long double>::infinity();
    for (int i = 0; i < n; ++i) {
        for (int j = i+1; j < n; ++j) {
            long double dx = pts[i][0] - pts[j][0];
            long double dy = pts[i][1] - pts[j][1];
            long double dz = pts[i][2] - pts[j][2];
            long double d2 = dx*dx + dy*dy + dz*dz;
            if (d2 < min_d2) min_d2 = d2;
        }
    }
    long double min_dist = sqrtl(min_d2);

    cout.setf(std::ios::fixed); 
    cout << setprecision(12) << (double)min_dist << "\n";
    for (int i = 0; i < n; ++i) {
        cout << setprecision(12)
             << (double)pts[i][0] << " " << (double)pts[i][1] << " " << (double)pts[i][2] << "\n";
    }

    return 0;
}