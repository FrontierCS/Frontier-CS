#include <iostream>
#include <vector>
#include <cmath>
#include <cstdio>
#include <algorithm>

using namespace std;

struct Point {
    double x, y, z;
};

double dist(const Point& a, const Point& b) {
    double dx = a.x - b.x;
    double dy = a.y - b.y;
    double dz = a.z - b.z;
    return sqrt(dx*dx + dy*dy + dz*dz);
}

void normalize(Point& p) {
    double len = sqrt(p.x*p.x + p.y*p.y + p.z*p.z);
    p.x /= len;
    p.y /= len;
    p.z /= len;
}

int main() {
    const double PI = acos(-1.0);
    int n;
    cin >> n;
    vector<Point> p(n);
    
    // Golden spiral initialization
    double golden_angle = PI * (3.0 - sqrt(5.0));
    for (int i = 0; i < n; ++i) {
        double y = 1.0 - (2.0 * i) / (n - 1.0);   // y from 1 down to -1
        double radius = sqrt(1.0 - y*y);
        double theta = golden_angle * i;
        double x = cos(theta) * radius;
        double z = sin(theta) * radius;
        p[i] = {x, y, z};
    }
    
    // Repulsion iterations
    double step = 0.1;
    double decay = 0.98;
    int iterations = 120;
    if (n > 500) iterations = 80;
    if (n > 800) iterations = 60;
    
    for (int it = 0; it < iterations; ++it) {
        vector<Point> forces(n, {0.0, 0.0, 0.0});
        // Compute all pairwise repulsive forces
        for (int i = 0; i < n; ++i) {
            for (int j = i+1; j < n; ++j) {
                double dx = p[i].x - p[j].x;
                double dy = p[i].y - p[j].y;
                double dz = p[i].z - p[j].z;
                double dist2 = dx*dx + dy*dy + dz*dz;
                if (dist2 < 1e-12) continue;   // too close, skip
                double dist = sqrt(dist2);
                double factor = 1.0 / (dist2 * dist);   // 1 / dist^3
                double fx = dx * factor;
                double fy = dy * factor;
                double fz = dz * factor;
                forces[i].x += fx;
                forces[i].y += fy;
                forces[i].z += fz;
                forces[j].x -= fx;
                forces[j].y -= fy;
                forces[j].z -= fz;
            }
        }
        // Apply forces and project back onto the sphere
        for (int i = 0; i < n; ++i) {
            p[i].x += step * forces[i].x;
            p[i].y += step * forces[i].y;
            p[i].z += step * forces[i].z;
            normalize(p[i]);
        }
        step *= decay;
    }
    
    // Compute minimum pairwise distance
    double min_dist = 2.0;
    for (int i = 0; i < n; ++i) {
        for (int j = i+1; j < n; ++j) {
            double d = dist(p[i], p[j]);
            if (d < min_dist) min_dist = d;
        }
    }
    
    // Output
    printf("%.10f\n", min_dist);
    for (int i = 0; i < n; ++i) {
        printf("%.10f %.10f %.10f\n", p[i].x, p[i].y, p[i].z);
    }
    
    return 0;
}