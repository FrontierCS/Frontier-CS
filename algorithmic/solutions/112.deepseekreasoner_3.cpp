#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>
#include <algorithm>

using namespace std;

struct Point {
    double x, y, z;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    const double golden_ratio = (1.0 + sqrt(5.0)) / 2.0;
    vector<Point> pts(n);

    // Fibonacci sphere initialisation
    for (int i = 0; i < n; ++i) {
        double y = 1.0 - (2.0 * i + 1.0) / n;
        double r = sqrt(1.0 - y * y);
        double theta = 2.0 * M_PI * i / golden_ratio;
        pts[i].x = cos(theta) * r;
        pts[i].z = sin(theta) * r;
        pts[i].y = y;
    }

    // Repulsion iterations
    const int MAX_ITER = 100;
    const double initial_step = 0.1;
    const double eps = 1e-30;

    for (int iter = 0; iter < MAX_ITER; ++iter) {
        double step = initial_step * (1.0 - iter / double(MAX_ITER));
        for (int i = 0; i < n; ++i) {
            double fx = 0.0, fy = 0.0, fz = 0.0;
            for (int j = 0; j < n; ++j) {
                if (i == j) continue;
                double dx = pts[i].x - pts[j].x;
                double dy = pts[i].y - pts[j].y;
                double dz = pts[i].z - pts[j].z;
                double dsq = dx*dx + dy*dy + dz*dz;
                double factor = 1.0 / (dsq + eps);
                fx += dx * factor;
                fy += dy * factor;
                fz += dz * factor;
            }
            pts[i].x += step * fx;
            pts[i].y += step * fy;
            pts[i].z += step * fz;
            // Project back onto the unit sphere
            double len = sqrt(pts[i].x*pts[i].x + pts[i].y*pts[i].y + pts[i].z*pts[i].z);
            pts[i].x /= len;
            pts[i].y /= len;
            pts[i].z /= len;
        }
    }

    // Compute minimum pairwise distance
    double minDist = 1e9;
    for (int i = 0; i < n; ++i) {
        for (int j = i+1; j < n; ++j) {
            double dx = pts[i].x - pts[j].x;
            double dy = pts[i].y - pts[j].y;
            double dz = pts[i].z - pts[j].z;
            double d = sqrt(dx*dx + dy*dy + dz*dz);
            if (d < minDist) minDist = d;
        }
    }

    cout << fixed << setprecision(10) << minDist << '\n';
    for (int i = 0; i < n; ++i) {
        cout << fixed << setprecision(10) << pts[i].x << ' ' << pts[i].y << ' ' << pts[i].z << '\n';
    }

    return 0;
}