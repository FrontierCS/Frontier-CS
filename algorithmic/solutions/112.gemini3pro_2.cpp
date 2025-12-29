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

// Normalize a point to lie on the unit sphere
inline void normalize(Point& p) {
    double magSq = p.x * p.x + p.y * p.y + p.z * p.z;
    if (magSq > 1e-18) {
        double mag = sqrt(magSq);
        p.x /= mag;
        p.y /= mag;
        p.z /= mag;
    } else {
        // Fallback for zero vector, though unlikely with our initialization
        p.x = 1.0; p.y = 0.0; p.z = 0.0;
    }
}

// Calculate squared Euclidean distance between two points
inline double distSq(const Point& a, const Point& b) {
    double dx = a.x - b.x;
    double dy = a.y - b.y;
    double dz = a.z - b.z;
    return dx*dx + dy*dy + dz*dz;
}

int main() {
    // Optimize standard I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    vector<Point> p(n);

    // 1. Initialization: Fibonacci Sphere Algorithm
    // This provides a near-optimal starting distribution, significantly better than random.
    double golden_ratio = (1.0 + sqrt(5.0)) / 2.0;
    for (int i = 0; i < n; ++i) {
        // Evenly distribute z coordinates from roughly 1 to -1
        double i_val = i + 0.5; 
        double z = 1.0 - (2.0 * i_val) / n; 
        
        // Radius at this z
        double r = sqrt(1.0 - z * z);
        
        // Golden angle increment
        double theta = 2.0 * M_PI * i_val / golden_ratio;
        
        p[i].x = r * cos(theta);
        p[i].y = r * sin(theta);
        p[i].z = z;
    }

    // 2. Optimization Phase: Repulsion Simulation
    // We simulate charged particles repelling each other.
    // To maximize minimum distance (Tammes problem), we want "hard" spheres.
    // We start with "soft" repulsion to arrange globally, then harden the potential over time.
    
    clock_t start_time = clock();
    double time_limit = 1.85; // Seconds (leave margin within 2.0s limit)
    
    // Annealing parameters
    double initial_step = 0.1;
    double final_step = 0.00001;

    vector<Point> forces(n);

    while (true) {
        double elapsed = (double)(clock() - start_time) / CLOCKS_PER_SEC;
        if (elapsed > time_limit) break;

        double progress = elapsed / time_limit;
        
        // Linearly interpolate exponent for force
        // Start with force ~ 1/d^4 (soft) -> End with force ~ 1/d^30 (hard)
        // We calculate factor = (1/d^2)^exp.
        // exp starts at 2 and goes up to 15.
        // Effective Force = vector * factor = d * (1/d^(2*exp)) = 1/d^(2*exp - 1)
        int base_exp = 2 + (int)(13.0 * progress);
        
        // Decay step size exponentially
        double step = initial_step * pow(final_step / initial_step, progress);
        
        // Reset forces
        for (int i = 0; i < n; ++i) {
            forces[i].x = 0;
            forces[i].y = 0;
            forces[i].z = 0;
        }

        // Compute pairwise repulsion
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                double dx = p[i].x - p[j].x;
                double dy = p[i].y - p[j].y;
                double dz = p[i].z - p[j].z;
                double d2 = dx*dx + dy*dy + dz*dz;
                
                // Avoid division by zero
                if (d2 < 1e-14) d2 = 1e-14;

                // Calculate force factor efficiently
                // factor = 1 / (d2 ^ base_exp)
                double inv_d2 = 1.0 / d2;
                double factor = inv_d2;
                for (int k = 1; k < base_exp; ++k) {
                    factor *= inv_d2;
                }
                
                // F_ij vector = factor * (dx, dy, dz)
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

        // Apply forces with normalization
        // We normalize the step so that the maximum displacement of any point is roughly 'step'.
        // This ensures stability regardless of the magnitude of forces (which grow huge with high base_exp).
        double max_f_sq = 0;
        for (int i = 0; i < n; ++i) {
            double f2 = forces[i].x*forces[i].x + forces[i].y*forces[i].y + forces[i].z*forces[i].z;
            if (f2 > max_f_sq) max_f_sq = f2;
        }

        if (max_f_sq > 1e-30) {
            double max_f = sqrt(max_f_sq);
            double scale = step / max_f;
            
            for (int i = 0; i < n; ++i) {
                p[i].x += forces[i].x * scale;
                p[i].y += forces[i].y * scale;
                p[i].z += forces[i].z * scale;
                // Project back to unit sphere
                normalize(p[i]);
            }
        }
    }

    // Calculate final minimum distance
    double min_dist_sq = 1e18;
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            double d = distSq(p[i], p[j]);
            if (d < min_dist_sq) min_dist_sq = d;
        }
    }

    // Output results
    cout << fixed << setprecision(10) << sqrt(min_dist_sq) << "\n";
    for (int i = 0; i < n; ++i) {
        cout << p[i].x << " " << p[i].y << " " << p[i].z << "\n";
    }

    return 0;
}