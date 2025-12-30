#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>
#include <algorithm>

const double PI = acos(-1.0);

struct Point {
    double x, y, z;

    Point& operator+=(const Point& other) {
        x += other.x; y += other.y; z += other.z;
        return *this;
    }
    Point& operator-=(const Point& other) {
        x -= other.x; y -= other.y; z -= other.z;
        return *this;
    }
    Point operator+(const Point& other) const {
        return {x + other.x, y + other.y, z + other.z};
    }
    Point operator-(const Point& other) const {
        return {x - other.x, y - other.y, z - other.z};
    }
    Point operator*(double scalar) const {
        return {x * scalar, y * scalar, z * scalar};
    }
    double dot(const Point& other) const {
        return x * other.x + y * other.y + z * other.z;
    }
    double length_sq() const {
        return x * x + y * y + z * z;
    }
    double length() const {
        return sqrt(length_sq());
    }
    Point normalize() const {
        double l = length();
        if (l < 1e-12) return {1, 0, 0}; // Fallback for zero vector
        return {x / l, y / l, z / l};
    }
};

void solve() {
    int n;
    std::cin >> n;

    if (n == 2) {
        std::cout << std::fixed << std::setprecision(10) << 2.0 << std::endl;
        std::cout << std::fixed << std::setprecision(10) << 0.0 << " " << 0.0 << " " << 1.0 << std::endl;
        std::cout << std::fixed << std::setprecision(10) << 0.0 << " " << 0.0 << " " << -1.0 << std::endl;
        return;
    }

    std::vector<Point> points(n);

    // Initialization using Fibonacci lattice
    const double golden_angle = PI * (3.0 - sqrt(5.0));

    for (int i = 0; i < n; ++i) {
        double y = 1.0 - (2.0 * i) / (n - 1.0);
        double radius = sqrt(1.0 - y * y);
        double theta = golden_angle * i;
        double x = cos(theta) * radius;
        double z = sin(theta) * radius;
        points[i] = {x, y, z};
    }
    
    // Adjust number of iterations based on N to fit time limit.
    int iterations = static_cast<int>(400000000.0 / (double(n) * n + 20000.0));
    iterations = std::max(iterations, 200);
    if (n < 30) {
        iterations = 20000;
    }

    double initial_step = 0.2 / sqrt(static_cast<double>(n));

    for (int iter = 0; iter < iterations; ++iter) {
        // Linearly decreasing step size
        double step = initial_step * (1.0 - (double)iter / iterations);
        step = std::max(step, initial_step * 0.01);

        std::vector<Point> forces(n, {0, 0, 0});
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                Point diff = points[i] - points[j];
                double dist_sq = diff.length_sq();
                if (dist_sq < 1e-14) dist_sq = 1e-14;
                
                // Repulsive force proportional to 1/r^3
                double inv_dist_sq = 1.0 / dist_sq;
                Point force_contrib = diff * inv_dist_sq * inv_dist_sq;
                
                forces[i] += force_contrib;
                forces[j] -= force_contrib;
            }
        }
        
        for (int i = 0; i < n; ++i) {
            Point p = points[i];
            Point F = forces[i];
            
            // Project force onto the tangent plane
            Point F_tangent = F - p * p.dot(F);
            
            if (F_tangent.length_sq() > 1e-20) {
                Point move_dir = F_tangent.normalize();
                points[i] = (p + move_dir * step).normalize();
            }
        }
    }

    double min_dist_sq = 100.0;
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            min_dist_sq = std::min(min_dist_sq, (points[i] - points[j]).length_sq());
        }
    }

    std::cout << std::fixed << std::setprecision(10) << sqrt(min_dist_sq) << std::endl;
    for (int i = 0; i < n; ++i) {
        std::cout << std::fixed << std::setprecision(10) << points[i].x << " " << points[i].y << " " << points[i].z << std::endl;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}