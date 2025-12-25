#include <iostream>
#include <vector>
#include <cmath>
#include <cstdio>
#include <algorithm>

using namespace std;

const double PI = acos(-1.0);

double dist2(const array<double,3>& a, const array<double,3>& b) {
    double dx = a[0] - b[0];
    double dy = a[1] - b[1];
    double dz = a[2] - b[2];
    return dx*dx + dy*dy + dz*dz;
}

int main() {
    int n;
    cin >> n;
    vector<array<double,3>> pts(n);
    
    // Special case: two antipodal points are optimal
    if (n == 2) {
        pts[0] = {0.0, 0.0, 1.0};
        pts[1] = {0.0, 0.0, -1.0};
        double min_d = 2.0;
        printf("%.12lf\n", min_d);
        for (int i = 0; i < n; ++i)
            printf("%.12lf %.12lf %.12lf\n", pts[i][0], pts[i][1], pts[i][2]);
        return 0;
    }
    
    // Fibonacci spiral (golden angle) initial distribution on the unit sphere
    double offset = 2.0 / n;
    double increment = PI * (3.0 - sqrt(5.0));   // golden angle in radians
    
    for (int i = 0; i < n; ++i) {
        double y = i * offset - 1.0 + offset / 2.0;
        double r = sqrt(1.0 - y * y);
        double phi = i * increment;
        double x = cos(phi) * r;
        double z = sin(phi) * r;
        pts[i] = {x, y, z};
    }
    
    // Compute initial minimal pairwise distance
    double best_min = 1e100;
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            double d2 = dist2(pts[i], pts[j]);
            if (d2 < best_min) best_min = d2;
        }
    }
    best_min = sqrt(best_min);
    auto best_pts = pts;
    
    // Repulsive force iterations to spread points further apart
    const int max_iter = 100;
    const double eps = 1e-12;
    double step = 0.1;
    double decay = 0.995;
    
    for (int iter = 0; iter < max_iter; ++iter) {
        vector<array<double,3>> disp(n, {0.0, 0.0, 0.0});
        
        // Compute forces (inverse square repulsion)
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                array<double,3> diff = {pts[i][0] - pts[j][0],
                                        pts[i][1] - pts[j][1],
                                        pts[i][2] - pts[j][2]};
                double d2 = diff[0]*diff[0] + diff[1]*diff[1] + diff[2]*diff[2];
                if (d2 < eps) continue;
                double inv_d2 = 1.0 / d2;
                disp[i][0] += diff[0] * inv_d2;
                disp[i][1] += diff[1] * inv_d2;
                disp[i][2] += diff[2] * inv_d2;
                disp[j][0] -= diff[0] * inv_d2;
                disp[j][1] -= diff[1] * inv_d2;
                disp[j][2] -= diff[2] * inv_d2;
            }
        }
        
        // Move points and project back onto the sphere
        for (int i = 0; i < n; ++i) {
            pts[i][0] += step * disp[i][0];
            pts[i][1] += step * disp[i][1];
            pts[i][2] += step * disp[i][2];
            double r = sqrt(pts[i][0]*pts[i][0] + pts[i][1]*pts[i][1] + pts[i][2]*pts[i][2]);
            if (r > eps) {
                pts[i][0] /= r;
                pts[i][1] /= r;
                pts[i][2] /= r;
            }
        }
        
        // Compute new minimal distance
        double cur_min = 1e100;
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                double d2 = dist2(pts[i], pts[j]);
                if (d2 < cur_min) cur_min = d2;
            }
        }
        cur_min = sqrt(cur_min);
        
        // Keep the best configuration found so far
        if (cur_min > best_min) {
            best_min = cur_min;
            best_pts = pts;
        }
        
        step *= decay;
        if (step < 1e-6) break;
    }
    
    // Output the result
    printf("%.12lf\n", best_min);
    for (int i = 0; i < n; ++i) {
        printf("%.12lf %.12lf %.12lf\n", best_pts[i][0], best_pts[i][1], best_pts[i][2]);
    }
    
    return 0;
}