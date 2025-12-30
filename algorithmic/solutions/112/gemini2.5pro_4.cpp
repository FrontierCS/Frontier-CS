#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>
#include <algorithm>
#include <numeric>

// Set up fast I/O
void setup_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

const double PI = acos(-1.0);

struct vec3 {
    double x, y, z;

    vec3() : x(0), y(0), z(0) {}
    vec3(double x, double y, double z) : x(x), y(y), z(z) {}

    vec3& operator+=(const vec3& other) {
        x += other.x; y += other.y; z += other.z;
        return *this;
    }
    vec3& operator-=(const vec3& other) {
        x -= other.x; y -= other.y; z -= other.z;
        return *this;
    }
    
    vec3 operator+(const vec3& other) const {
        return {x + other.x, y + other.y, z + other.z};
    }
    vec3 operator-(const vec3& other) const {
        return {x - other.x, y - other.y, z - other.z};
    }
    vec3 operator*(double s) const {
        return {x * s, y * s, z * s};
    }
    vec3 operator/(double s) const {
        return {x / s, y / s, z / s};
    }
    
    double norm_sq() const {
        return x * x + y * y + z * z;
    }
    double norm() const {
        return sqrt(norm_sq());
    }
    void normalize() {
        double n = norm();
        if (n > 1e-12) {
            x /= n; y /= n; z /= n;
        }
    }
};

void solve_general(int n, std::vector<vec3>& points) {
    points.resize(n);
    
    // Initialize with Fibonacci sphere for a good starting distribution
    const double PHI = (1.0 + sqrt(5.0)) / 2.0;
    for (int i = 0; i < n; ++i) {
        double y = 1.0 - (2.0 * (i + 0.5)) / n;
        double radius = sqrt(1.0 - y * y);
        double theta = 2.0 * PI * i / PHI;
        points[i] = {cos(theta) * radius, y, sin(theta) * radius};
    }

    // Simulation parameters adapt to n
    long long total_effort = 400000000LL;
    int iterations = total_effort / ((long long)n * n + 1);
    iterations = std::max(500, std::min(20000, iterations));
    
    double alpha = 0.2 / sqrt(n);
    double decay_rate = pow(0.01, 1.0 / iterations);

    for (int iter = 0; iter < iterations; ++iter) {
        std::vector<vec3> forces(n, {0, 0, 0});
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                vec3 diff = points[i] - points[j];
                double dist_sq = diff.norm_sq();
                if (dist_sq < 1e-12) dist_sq = 1e-12;
                vec3 force = diff / (dist_sq * dist_sq);
                forces[i] += force;
                forces[j] -= force;
            }
        }

        for (int i = 0; i < n; ++i) {
            points[i] += forces[i] * alpha;
            points[i].normalize();
        }

        alpha *= decay_rate;
    }
}


int main() {
    setup_io();

    int n;
    std::cin >> n;

    std::vector<vec3> points;
    
    if (n == 2) {
        points.push_back({0, 0, 1});
        points.push_back({0, 0, -1});
    } else if (n == 3) {
        points.push_back({1, 0, 0});
        points.push_back({-0.5, sqrt(3.0)/2.0, 0});
        points.push_back({-0.5, -sqrt(3.0)/2.0, 0});
    } else if (n == 4) {
        double s = 1.0 / sqrt(3.0);
        points.push_back({s, s, s});
        points.push_back({s, -s, -s});
        points.push_back({-s, s, -s});
        points.push_back({-s, -s, s});
    } else if (n == 6) {
        points.push_back({1, 0, 0}); points.push_back({-1, 0, 0});
        points.push_back({0, 1, 0}); points.push_back({0, -1, 0});
        points.push_back({0, 0, 1}); points.push_back({0, 0, -1});
    } else if (n == 12) {
        double phi = (1.0 + sqrt(5.0)) / 2.0;
        double c = 1.0 / sqrt(1 + phi*phi);
        double cp = c * phi;
        points.push_back({-c, cp, 0}); points.push_back({c, cp, 0});
        points.push_back({-c, -cp, 0}); points.push_back({c, -cp, 0});
        points.push_back({0, -c, cp}); points.push_back({0, c, cp});
        points.push_back({0, -c, -cp}); points.push_back({0, c, -cp});
        points.push_back({-cp, 0, -c}); points.push_back({cp, 0, -c});
        points.push_back({-cp, 0, c}); points.push_back({cp, 0, c});
    } else {
        solve_general(n, points);
    }

    double min_dist_sq = 100.0;
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            min_dist_sq = std::min(min_dist_sq, (points[i] - points[j]).norm_sq());
        }
    }

    std::cout << std::fixed << std::setprecision(15) << sqrt(min_dist_sq) << "\n";
    for (const auto& p : points) {
        std::cout << std::fixed << std::setprecision(15) << p.x << " " << p.y << " " << p.z << "\n";
    }
    
    return 0;
}