#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>
#include <chrono>
#include <algorithm>
#include <numeric>

// Using long double for PI for better precision, though double is likely sufficient
const long double PI = acos(-1.0L);

struct Point {
    double x = 0.0, y = 0.0, z = 0.0;

    Point operator+(const Point& other) const { return {x + other.x, y + other.y, z + other.z}; }
    Point& operator+=(const Point& other) { x += other.x; y += other.y; z += other.z; return *this; }
    Point operator-(const Point& other) const { return {x - other.x, y - other.y, z - other.z}; }
    Point& operator-=(const Point& other) { x -= other.x; y -= other.y; z -= other.z; return *this; }
    Point operator*(double s) const { return {x * s, y * s, z * s}; }
    Point operator/(double s) const { return {x / s, y / s, z / s}; }

    double dot(const Point& other) const { return x * other.x + y * other.y + z * other.z; }
    double norm_sq() const { return x * x + y * y + z * z; }
    double norm() const { return std::sqrt(norm_sq()); }

    void normalize() {
        double n = norm();
        if (n > 1e-12) {
            x /= n; y /= n; z /= n;
        }
    }
};

// Generates a good initial distribution of points on the sphere using a Fibonacci lattice.
void generate_fibonacci_lattice(std::vector<Point>& points, int n) {
    const double golden_ratio = (1.0 + std::sqrt(5.0)) / 2.0;
    for (int i = 0; i < n; ++i) {
        double z = (2.0 * i + 1.0) / n - 1.0;
        double r = std::sqrt(1.0 - z * z);
        double phi = 2 * PI * i / golden_ratio;
        points[i] = {r * std::cos(phi), r * std::sin(phi), z};
    }
}

void solve() {
    int n;
    std::cin >> n;

    if (n == 2) {
        std::cout << std::fixed << std::setprecision(10) << 2.0 << std::endl;
        std::cout << "0.0 0.0 1.0" << std::endl;
        std::cout << "0.0 0.0 -1.0" << std::endl;
        return;
    }

    std::vector<Point> points(n);
    generate_fibonacci_lattice(points, n);

    auto start_time = std::chrono::high_resolution_clock::now();
    const double time_limit = 1.85;

    double alpha = 0.02; // Initial step size as a distance

    while (std::chrono::duration<double>(std::chrono::high_resolution_clock::now() - start_time).count() < time_limit) {
        std::vector<Point> forces(n);
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                Point diff = points[i] - points[j];
                double dist_sq = diff.norm_sq();
                if (dist_sq < 1e-14) dist_sq = 1e-14; // Prevent division by zero
                Point force = diff / dist_sq; // Force proportional to 1/d^2
                forces[i] += force;
                forces[j] -= force;
            }
        }

        for (int i = 0; i < n; ++i) {
            // Project force onto the tangent plane
            Point normal = points[i];
            Point tangent_force = forces[i] - normal * forces[i].dot(normal);
            double force_mag = tangent_force.norm();

            if (force_mag > 1e-12) {
                // Move the point by a distance 'alpha' along the tangential force direction
                points[i] += tangent_force * (alpha / force_mag);
            }
            // Re-project the point back onto the unit sphere
            points[i].normalize();
        }
        
        // Anneal the step size
        alpha *= 0.999;
    }

    double min_dist_sq = 4.0; // Max possible squared distance is (2*R)^2 = 4
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            min_dist_sq = std::min(min_dist_sq, (points[i] - points[j]).norm_sq());
        }
    }

    std::cout << std::fixed << std::setprecision(10) << std::sqrt(min_dist_sq) << std::endl;
    for (const auto& p : points) {
        std::cout << std::fixed << std::setprecision(10) << p.x << " " << p.y << " " << p.z << std::endl;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}