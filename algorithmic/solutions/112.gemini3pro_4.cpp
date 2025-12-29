#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <ctime>

using namespace std;

// Structure to represent a point in 3D space
struct Point {
    double x, y, z;
};

// Calculate squared Euclidean distance between two points
inline double distSq(const Point& a, const Point& b) {
    double dx = a.x - b.x;
    double dy = a.y - b.y;
    double dz = a.z - b.z;
    return dx*dx + dy*dy + dz*dz;
}

// Project point onto the unit sphere
inline void normalize(Point& p) {
    double len2 = p.x*p.x + p.y*p.y + p.z*p.z;
    if (len2 > 1e-20) {
        double invLen = 1.0 / sqrt(len2);
        p.x *= invLen;
        p.y *= invLen;
        p.z *= invLen;
    } else {
        // Fallback for zero vector (unlikely)
        p.x = 1.0; p.y = 0.0; p.z = 0.0;
    }
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    vector<Point> p(n);

    // 1. Initialization: Fibonacci Sphere Lattice
    // This provides a deterministic, evenly spaced distribution to start with.
    double phi = acos(-1.0) * (3.0 - sqrt(5.0)); // Golden angle
    for (int i = 0; i < n; ++i) {
        // y coordinate distributed from roughly 1 to -1
        // (i + 0.5) / n offset provides equal area bands
        double y = 1.0 - (i + 0.5) * 2.0 / n;
        
        double radius = sqrt(max(0.0, 1.0 - y * y));
        double theta = phi * i;

        p[i].x = radius * cos(theta);
        p[i].z = radius * sin(theta);
        p[i].y = y;
    }

    // 2. Optimization: Repulsive Force Simulation
    // We treat points as particles repelling each other to maximize mutual distances.
    double start_time = (double)clock() / CLOCKS_PER_SEC;
    // We stop a bit before 2.0s to allow for final calculations and printing
    double time_limit = 1.80; 

    // Simulation parameters
    // Step size determines how much points move. We decay it over time.
    double step = 0.1;
    // Minimum step size 
    double min_step = 1e-5; 
    
    // Arrays to accumulate forces
    vector<double> dx(n), dy(n), dz(n);

    int iter = 0;
    while (true) {
        // Time check every 64 iterations to minimize overhead
        if ((iter & 63) == 0) {
            double curr_time = (double)clock() / CLOCKS_PER_SEC;
            if (curr_time - start_time > time_limit) break;
        }

        // Decay step size
        step *= 0.995;
        if (step < min_step) step = min_step;

        // Reset forces
        fill(dx.begin(), dx.end(), 0.0);
        fill(dy.begin(), dy.end(), 0.0);
        fill(dz.begin(), dz.end(), 0.0);

        // Compute repulsive forces
        // To maximize min distance, we use a force that drops off with distance.
        // We use a relatively steep potential (roughly 1/r^6 scaling) to approximate 
        // the max-min objective ("hard spheres").
        
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                double d2 = distSq(p[i], p[j]);
                // Avoid division by zero
                if (d2 < 1e-10) d2 = 1e-10;

                // Weight factor: 1 / (d^2)^3 = 1/d^6
                // Force vector = (pi - pj) * factor
                double factor = 1.0 / (d2 * d2 * d2);

                double offx = (p[i].x - p[j].x) * factor;
                double offy = (p[i].y - p[j].y) * factor;
                double offz = (p[i].z - p[j].z) * factor;

                dx[i] += offx;
                dy[i] += offy;
                dz[i] += offz;

                dx[j] -= offx;
                dy[j] -= offy;
                dz[j] -= offz;
            }
        }

        // Apply forces and project back to sphere
        for (int i = 0; i < n; ++i) {
            double fx = dx[i];
            double fy = dy[i];
            double fz = dz[i];
            
            double f_magSq = fx*fx + fy*fy + fz*fz;
            
            // Limit movement per iteration to ensure stability
            // Displacement = Force * scale. 
            // We ensure displacement <= max_disp.
            double max_disp = 0.05; 
            double scale = step;
            
            if (f_magSq * step * step > max_disp * max_disp) {
                 scale = max_disp / sqrt(f_magSq);
            }

            p[i].x += fx * scale;
            p[i].y += fy * scale;
            p[i].z += fz * scale;

            normalize(p[i]);
        }
        
        iter++;
    }

    // 3. Compute Result
    double min_dist_sq = 1e18;
    // Safety for degenerate case n < 2, though constraints say n >= 2
    if (n < 2) min_dist_sq = 0; 

    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            double d2 = distSq(p[i], p[j]);
            if (d2 < min_dist_sq) min_dist_sq = d2;
        }
    }

    double min_dist = sqrt(min_dist_sq);

    // 4. Output
    cout << fixed << setprecision(10) << min_dist << "\n";
    for (int i = 0; i < n; ++i) {
        cout << p[i].x << " " << p[i].y << " " << p[i].z << "\n";
    }

    return 0;
}