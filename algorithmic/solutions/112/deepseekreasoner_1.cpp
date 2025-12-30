#include <cstdio>
#include <cmath>
#include <vector>
#include <algorithm>

struct Point {
    double x, y, z;
    Point() : x(0), y(0), z(0) {}
    Point(double x, double y, double z) : x(x), y(y), z(z) {}
};

int main() {
    int n;
    scanf("%d", &n);
    std::vector<Point> p(n);
    
    // Fibonacci spiral (golden angle) initialization
    const double phi = M_PI * (3.0 - sqrt(5.0)); // golden angle in radians
    for (int i = 0; i < n; ++i) {
        double y = 1.0 - (2.0 * i) / (n - 1);          // from 1 to -1
        double radius = sqrt(1.0 - y * y);
        double theta = phi * i;
        double x = cos(theta) * radius;
        double z = sin(theta) * radius;
        p[i] = Point(x, y, z);
    }
    
    // Gradient descent for 1/r^2 potential (Thomson-like)
    int max_iter = 200;
    double alpha = 0.1;
    for (int iter = 0; iter < max_iter; ++iter) {
        std::vector<Point> force(n, Point(0,0,0));
        // Compute pairwise forces
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                double dx = p[i].x - p[j].x;
                double dy = p[i].y - p[j].y;
                double dz = p[i].z - p[j].z;
                double d2 = dx*dx + dy*dy + dz*dz;
                if (d2 < 1e-12) continue;
                double inv_d2 = 1.0 / d2;
                double factor = 2.0 * inv_d2 * inv_d2;   // 2 / d^4
                force[i].x += factor * dx;
                force[i].y += factor * dy;
                force[i].z += factor * dz;
                force[j].x -= factor * dx;
                force[j].y -= factor * dy;
                force[j].z -= factor * dz;
            }
        }
        // Move each point tangentially and renormalize
        for (int i = 0; i < n; ++i) {
            double dot = force[i].x * p[i].x + force[i].y * p[i].y + force[i].z * p[i].z;
            double tx = force[i].x - dot * p[i].x;
            double ty = force[i].y - dot * p[i].y;
            double tz = force[i].z - dot * p[i].z;
            p[i].x += alpha * tx;
            p[i].y += alpha * ty;
            p[i].z += alpha * tz;
            double len = sqrt(p[i].x*p[i].x + p[i].y*p[i].y + p[i].z*p[i].z);
            if (len > 1e-12) {
                p[i].x /= len;
                p[i].y /= len;
                p[i].z /= len;
            }
        }
        alpha *= 0.99;   // decay step size
    }
    
    // Compute minimum pairwise distance
    double min_sq = 4.0;
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            double dx = p[i].x - p[j].x;
            double dy = p[i].y - p[j].y;
            double dz = p[i].z - p[j].z;
            double d2 = dx*dx + dy*dy + dz*dz;
            if (d2 < min_sq) min_sq = d2;
        }
    }
    double min_dist = sqrt(min_sq);
    
    // Output
    printf("%.12f\n", min_dist);
    for (int i = 0; i < n; ++i) {
        printf("%.12f %.12f %.12f\n", p[i].x, p[i].y, p[i].z);
    }
    return 0;
}