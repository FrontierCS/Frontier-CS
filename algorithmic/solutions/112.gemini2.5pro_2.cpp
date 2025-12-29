#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>
#include <algorithm>
#include <numeric>

using LD = long double;

const LD PI = acos(-1.0L);

struct Point {
    LD x, y, z;
};

Point operator+(const Point& a, const Point& b) { return {a.x + b.x, a.y + b.y, a.z + b.z}; }
Point& operator+=(Point& a, const Point& b) { a.x += b.x; a.y += b.y; a.z += b.z; return a; }
Point operator-(const Point& a, const Point& b) { return {a.x - b.x, a.y - b.y, a.z - b.z}; }
Point& operator-=(Point& a, const Point& b) { a.x -= b.x; a.y -= b.y; a.z -= b.z; return a; }
Point operator*(const Point& a, LD s) { return {a.x * s, a.y * s, a.z * s}; }

LD norm_sq(const Point& a) { return a.x * a.x + a.y * a.y + a.z * a.z; }

void normalize(Point& a) {
    LD mag = sqrt(norm_sq(a));
    if (mag > 1e-12L) {
        a.x /= mag;
        a.y /= mag;
        a.z /= mag;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    if (n == 2) {
        std::cout << std::fixed << std::setprecision(15) << 2.0L << "\n";
        std::cout << "0.0 0.0 1.0\n";
        std::cout << "0.0 0.0 -1.0\n";
        return 0;
    }

    std::vector<Point> points(n);

    const LD GOLDEN_RATIO = (1.0L + sqrt(5.0L)) / 2.0L;
    for (int i = 0; i < n; ++i) {
        LD z = 1.0L - (2.0L * (i + 0.5L)) / n;
        LD radius = sqrt(1.0L - z * z);
        LD theta = 2.0L * PI * (i + 0.5L) / GOLDEN_RATIO;
        points[i] = {cos(theta) * radius, sin(theta) * radius, z};
    }
    
    int iterations = std::min(15000, static_cast<int>(150000000.0L / (n * n) + 1));
    
    LD alpha_initial = 0.2L;
    LD alpha_final = 1e-5L;
    LD decay_factor = pow(alpha_final / alpha_initial, 1.0L / iterations);
    LD alpha = alpha_initial;

    for (int iter = 0; iter < iterations; ++iter) {
        std::vector<Point> forces(n, {0, 0, 0});
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                Point diff = points[i] - points[j];
                LD d2 = norm_sq(diff);
                if (d2 < 1e-14L) d2 = 1e-14L;

                LD inv_d4 = 1.0L / (d2 * d2);
                Point force_vec = diff * inv_d4;

                forces[i] += force_vec;
                forces[j] -= force_vec;
            }
        }

        for (int i = 0; i < n; ++i) {
            points[i] += forces[i] * alpha;
            normalize(points[i]);
        }
        
        alpha *= decay_factor;
    }

    LD min_dist2 = 100.0L;
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            min_dist2 = std::min(min_dist2, norm_sq(points[i] - points[j]));
        }
    }

    std::cout << std::fixed << std::setprecision(15);
    std::cout << sqrt(min_dist2) << "\n";
    for (int i = 0; i < n; ++i) {
        std::cout << points[i].x << " " << points[i].y << " " << points[i].z << "\n";
    }

    return 0;
}