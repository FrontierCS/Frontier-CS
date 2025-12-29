#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <random>
#include <iomanip>

using namespace std;

struct Point {
    double x, y, z;
    Point() : x(0), y(0), z(0) {}
    Point(double x_, double y_, double z_) : x(x_), y(y_), z(z_) {}
};

Point operator+(const Point& a, const Point& b) {
    return Point(a.x+b.x, a.y+b.y, a.z+b.z);
}
Point operator-(const Point& a, const Point& b) {
    return Point(a.x-b.x, a.y-b.y, a.z-b.z);
}
Point operator*(const Point& p, double s) {
    return Point(p.x*s, p.y*s, p.z*s);
}
Point operator/(const Point& p, double s) {
    return Point(p.x/s, p.y/s, p.z/s);
}
double dot(const Point& a, const Point& b) {
    return a.x*b.x + a.y*b.y + a.z*b.z;
}
double norm(const Point& p) {
    return sqrt(dot(p, p));
}
Point normalize(const Point& p) {
    double n = norm(p);
    if (n < 1e-12) return Point(0,0,1);
    return p / n;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    cout << fixed << setprecision(10);

    int n;
    cin >> n;

    if (n == 2) {
        // Optimal: antipodal points
        cout << "2.0000000000\n";
        cout << "0.0000000000 0.0000000000 1.0000000000\n";
        cout << "0.0000000000 0.0000000000 -1.0000000000\n";
        return 0;
    }

    // Generate initial points using Fibonacci spiral
    const double golden_angle = M_PI * (3.0 - sqrt(5.0));  // ~2.399963
    vector<Point> pts(n);
    for (int i = 0; i < n; ++i) {
        double y = 1.0 - (2.0 * i + 1.0) / n;   // from 1-1/n to -1+1/n
        double r = sqrt(1.0 - y*y);
        double phi = golden_angle * i;
        double x = cos(phi) * r;
        double z = sin(phi) * r;
        pts[i] = Point(x, y, z);
    }

    // Add small random perturbation to break symmetry
    mt19937 rng(12345 + n);
    uniform_real_distribution<double> dist(-0.01, 0.01);
    for (int i = 0; i < n; ++i) {
        Point rnd(dist(rng), dist(rng), dist(rng));
        pts[i] = normalize(pts[i] + rnd);
    }

    const int max_iter = 200;
    const double step_start = 0.08;
    const double decay = 0.995;
    double step = step_start;

    double best_min = 0.0;
    vector<Point> best_pts = pts;

    for (int iter = 0; iter < max_iter; ++iter) {
        // Compute minimal distance and forces
        double cur_min = 1e9;
        vector<Point> forces(n, Point(0,0,0));

        for (int i = 0; i < n; ++i) {
            for (int j = i+1; j < n; ++j) {
                Point diff = pts[i] - pts[j];
                double sq = dot(diff, diff);
                if (sq < 1e-12) continue;
                double dist = sqrt(sq);
                if (dist < cur_min) cur_min = dist;
                double inv_sq = 1.0 / sq;
                forces[i] = forces[i] + diff * inv_sq;
                forces[j] = forces[j] - diff * inv_sq;
            }
        }

        // Update best configuration
        if (cur_min > best_min) {
            best_min = cur_min;
            best_pts = pts;
        }

        // Move points
        for (int i = 0; i < n; ++i) {
            pts[i] = pts[i] + forces[i] * step;
            pts[i] = normalize(pts[i]);
        }

        // Cooling
        step *= decay;
    }

    // Output best found
    cout << best_min << "\n";
    for (int i = 0; i < n; ++i) {
        cout << best_pts[i].x << " " << best_pts[i].y << " " << best_pts[i].z << "\n";
    }

    return 0;
}