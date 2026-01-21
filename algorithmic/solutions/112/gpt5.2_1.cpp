#include <bits/stdc++.h>
using namespace std;

struct P {
    double x, y, z;
};

static inline double sqr(double v){ return v*v; }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<P> pts;
    pts.reserve(n);

    auto normalize = [](P p) -> P {
        double len2 = p.x*p.x + p.y*p.y + p.z*p.z;
        if (len2 > 1.0) {
            double inv = 1.0 / sqrt(len2);
            p.x *= inv; p.y *= inv; p.z *= inv;
        }
        return p;
    };

    if (n == 2) {
        pts.push_back({0.0, 0.0, 1.0});
        pts.push_back({0.0, 0.0, -1.0});
    } else if (n == 3) {
        for (int i = 0; i < 3; i++) {
            double ang = 2.0 * M_PI * i / 3.0;
            pts.push_back({cos(ang), sin(ang), 0.0});
        }
    } else if (n == 4) {
        double inv = 1.0 / sqrt(3.0);
        pts.push_back({ inv,  inv,  inv});
        pts.push_back({-inv, -inv,  inv});
        pts.push_back({-inv,  inv, -inv});
        pts.push_back({ inv, -inv, -inv});
    } else if (n == 6) {
        pts.push_back({ 1.0, 0.0, 0.0});
        pts.push_back({-1.0, 0.0, 0.0});
        pts.push_back({ 0.0, 1.0, 0.0});
        pts.push_back({ 0.0,-1.0, 0.0});
        pts.push_back({ 0.0, 0.0, 1.0});
        pts.push_back({ 0.0, 0.0,-1.0});
    } else if (n == 12) {
        double phi = (1.0 + sqrt(5.0)) / 2.0;
        vector<P> v = {
            {0,  1,  phi}, {0, -1,  phi}, {0,  1, -phi}, {0, -1, -phi},
            { 1,  phi, 0}, {-1,  phi, 0}, { 1, -phi, 0}, {-1, -phi, 0},
            { phi, 0,  1}, { phi, 0, -1}, {-phi, 0,  1}, {-phi, 0, -1}
        };
        pts.clear();
        for (auto p : v) pts.push_back(normalize(p));
    } else {
        double ga = M_PI * (3.0 - sqrt(5.0)); // golden angle
        for (int i = 0; i < n; i++) {
            double z = 1.0 - 2.0 * (i + 0.5) / (double)n;
            double r = sqrt(max(0.0, 1.0 - z*z));
            double t = ga * i;
            P p{r * cos(t), r * sin(t), z};
            pts.push_back(normalize(p));
        }
    }

    // Ensure size n in rare special cases (should not happen)
    if ((int)pts.size() != n) pts.resize(n);

    double min_d2 = numeric_limits<double>::infinity();
    for (int i = 0; i < n; i++) {
        for (int j = i + 1; j < n; j++) {
            double dx = pts[i].x - pts[j].x;
            double dy = pts[i].y - pts[j].y;
            double dz = pts[i].z - pts[j].z;
            double d2 = dx*dx + dy*dy + dz*dz;
            if (d2 < min_d2) min_d2 = d2;
        }
    }
    double min_dist = sqrt(min_d2);

    cout.setf(std::ios::fixed);
    cout << setprecision(15) << min_dist << "\n";
    for (int i = 0; i < n; i++) {
        // Safety: ensure within unit sphere
        P p = normalize(pts[i]);
        cout << setprecision(15) << p.x << " " << p.y << " " << p.z << "\n";
    }
    return 0;
}