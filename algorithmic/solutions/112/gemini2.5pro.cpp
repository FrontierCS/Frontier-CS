#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>
#include <numeric>
#include <algorithm>

using ld = long double;

const ld PI = acosl(-1.0L);

struct Point {
    ld x, y, z;

    Point operator+(const Point& other) const {
        return {x + other.x, y + other.y, z + other.z};
    }
    Point& operator+=(const Point& other) {
        x += other.x; y += other.y; z += other.z;
        return *this;
    }
    Point operator-(const Point& other) const {
        return {x - other.x, y - other.y, z - other.z};
    }
    Point& operator-=(const Point& other) {
        x -= other.x; y -= other.y; z -= other.z;
        return *this;
    }
    Point operator*(ld scalar) const {
        return {x * scalar, y * scalar, z * scalar};
    }
    ld dot(const Point& other) const {
        return x * other.x + y * other.y + z * other.z;
    }
    ld norm_sq() const {
        return x * x + y * y + z * z;
    }
    void normalize() {
        ld len = sqrtl(norm_sq());
        if (len > 1e-12L) {
            x /= len;
            y /= len;
            z /= len;
        }
    }
};

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<Point> points(n);

    // Initialize points using Fibonacci lattice
    const ld golden_angle = PI * (3.0L - sqrtl(5.0L));
    for (int i = 0; i < n; ++i) {
        ld z_coord = 1.0L - (2.0L * (i + 0.5L)) / n;
        ld radius = sqrtl(1.0L - z_coord * z_coord);
        ld theta = golden_angle * i;
        points[i] = {radius * cosl(theta), radius * sinl(theta), z_coord};
    }

    int iterations;
    if (n < 20) {
        iterations = 20000;
    } else {
        iterations = std::min(5000, static_cast<int>(40000000.0 / ((ld)n * n + 1.0)));
    }

    ld step_size = 0.2L;
    ld decay = 0.998L;

    for (int iter = 0; iter < iterations; ++iter) {
        std::vector<Point> forces(n, {0.0L, 0.0L, 0.0L});
        
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                Point diff = points[i] - points[j];
                ld dist_sq = diff.norm_sq();
                if (dist_sq < 1e-12L) dist_sq = 1e-12L;
                
                // Potential ~ 1/r^2, Force ~ d/r^4
                ld force_magnitude = 1.0L / (dist_sq * dist_sq);
                Point force_vec = diff * force_magnitude;
                
                forces[i] += force_vec;
                forces[j] -= force_vec;
            }
        }
        
        for (int i = 0; i < n; ++i) {
            // Project force onto the tangent plane
            ld dot_product = forces[i].dot(points[i]);
            Point tangent_force = forces[i] - (points[i] * dot_product);
            
            points[i] += tangent_force * step_size;
            points[i].normalize();
        }
        
        step_size *= decay;
    }

    ld min_dist_sq = 100.0L;
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            min_dist_sq = std::min(min_dist_sq, (points[i] - points[j]).norm_sq());
        }
    }

    std::cout << std::fixed << std::setprecision(15) << sqrtl(min_dist_sq) << std::endl;
    for (int i = 0; i < n; ++i) {
        std::cout << std::fixed << std::setprecision(15) << points[i].x << " " << points[i].y << " " << points[i].z << std::endl;
    }

    return 0;
}