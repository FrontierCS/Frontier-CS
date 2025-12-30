#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <cstdlib>

using namespace std;

struct Point {
    double x, y, z;
};

int main() {
    int n;
    cin >> n;
    
    // Initialization: cubic grid
    int L = ceil(pow(n, 1.0/3.0));
    double spacing = 1.0 / L;
    vector<Point> pts;
    pts.reserve(n);
    for (int i = 0; i < L; i++) {
        for (int j = 0; j < L; j++) {
            for (int k = 0; k < L; k++) {
                if (pts.size() >= n) break;
                double x = (i + 0.5) * spacing;
                double y = (j + 0.5) * spacing;
                double z = (k + 0.5) * spacing;
                pts.push_back({x, y, z});
            }
            if (pts.size() >= n) break;
        }
        if (pts.size() >= n) break;
    }
    // In case we still need more (should not happen), fill with random
    srand(12345);
    while (pts.size() < n) {
        double x = rand() / (double)RAND_MAX;
        double y = rand() / (double)RAND_MAX;
        double z = rand() / (double)RAND_MAX;
        pts.push_back({x, y, z});
    }
    
    // Parameters for force-directed refinement
    double r_des = 0.5 * spacing;               // initial desired radius
    const double step_size = 0.1;
    const int iterations = 30;
    const double r_inc = 1.02;                  // increment factor for r_des each iteration
    const double eps = 1e-12;
    
    for (int iter = 0; iter < iterations; iter++) {
        vector<Point> forces(n, {0.0, 0.0, 0.0});
        
        // Pairwise repulsion
        for (int i = 0; i < n; i++) {
            for (int j = i+1; j < n; j++) {
                double dx = pts[j].x - pts[i].x;
                double dy = pts[j].y - pts[i].y;
                double dz = pts[j].z - pts[i].z;
                double d2 = dx*dx + dy*dy + dz*dz;
                double r2 = r_des * r_des;
                if (d2 < r2) {
                    if (d2 < eps) d2 = eps;
                    double factor = (r2 / d2 - 1.0);
                    forces[i].x -= factor * dx;
                    forces[i].y -= factor * dy;
                    forces[i].z -= factor * dz;
                    forces[j].x += factor * dx;
                    forces[j].y += factor * dy;
                    forces[j].z += factor * dz;
                }
            }
        }
        
        // Wall repulsion
        for (int i = 0; i < n; i++) {
            double x = pts[i].x, y = pts[i].y, z = pts[i].z;
            // left wall
            if (x < r_des) {
                double denom = max(x, eps);
                double factor = (r_des / denom - 1.0);
                forces[i].x += factor;
            }
            // right wall
            if (1.0 - x < r_des) {
                double denom = max(1.0 - x, eps);
                double factor = (r_des / denom - 1.0);
                forces[i].x -= factor;
            }
            // bottom wall (y=0)
            if (y < r_des) {
                double denom = max(y, eps);
                double factor = (r_des / denom - 1.0);
                forces[i].y += factor;
            }
            // top wall (y=1)
            if (1.0 - y < r_des) {
                double denom = max(1.0 - y, eps);
                double factor = (r_des / denom - 1.0);
                forces[i].y -= factor;
            }
            // back wall (z=0)
            if (z < r_des) {
                double denom = max(z, eps);
                double factor = (r_des / denom - 1.0);
                forces[i].z += factor;
            }
            // front wall (z=1)
            if (1.0 - z < r_des) {
                double denom = max(1.0 - z, eps);
                double factor = (r_des / denom - 1.0);
                forces[i].z -= factor;
            }
        }
        
        // Apply forces
        for (int i = 0; i < n; i++) {
            double fx = forces[i].x;
            double fy = forces[i].y;
            double fz = forces[i].z;
            double len = sqrt(fx*fx + fy*fy + fz*fz);
            if (len > 0) {
                double scale = step_size * min(len, r_des*0.5) / len;
                pts[i].x += fx * scale;
                pts[i].y += fy * scale;
                pts[i].z += fz * scale;
                // Clamp to [0,1]
                pts[i].x = max(0.0, min(1.0, pts[i].x));
                pts[i].y = max(0.0, min(1.0, pts[i].y));
                pts[i].z = max(0.0, min(1.0, pts[i].z));
            }
        }
        
        // Increase desired radius
        r_des *= r_inc;
    }
    
    // Output with sufficient precision
    cout.precision(10);
    for (int i = 0; i < n; i++) {
        cout << pts[i].x << " " << pts[i].y << " " << pts[i].z << "\n";
    }
    
    return 0;
}