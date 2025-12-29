#include <iostream>
#include <vector>
#include <cmath>
#include <ctime>
#include <algorithm>
#include <iomanip>

using namespace std;

// Define a structure for 3D points
struct Point {
    double x, y, z;
};

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // Vectors to store points and force components
    vector<Point> p(n);
    vector<Point> forces(n);

    // Constant for the golden angle used in Fibonacci sphere initialization
    double golden_angle = M_PI * (3.0 - sqrt(5.0));

    // Initialize points using the Fibonacci Sphere algorithm
    // This provides a near-optimal starting distribution
    for (int i = 0; i < n; ++i) {
        double z = 1.0 - (2.0 * i + 1.0) / n; 
        double r = sqrt(max(0.0, 1.0 - z * z));
        double theta = golden_angle * i;
        p[i].x = r * cos(theta);
        p[i].y = r * sin(theta);
        p[i].z = z;
    }

    // Timer setup to stay within execution time limit
    clock_t start_time = clock();
    double time_limit = 1.8 * CLOCKS_PER_SEC; // Allow some buffer
    
    // Optimization parameters
    // alpha: base step size multiplier
    // move_limit: maximum distance a point can move in one iteration
    double alpha = 0.5;
    // Heuristic for initial move limit based on expected separation
    double move_limit = 0.1 / sqrt((double)n);
    
    int iter = 0;
    while (true) {
        // Check time every 64 iterations to minimize overhead
        if ((iter & 63) == 0) {
            if (clock() - start_time > time_limit) break;
        }
        iter++;

        // Reset forces
        for(int i=0; i<n; ++i) {
            forces[i].x = 0;
            forces[i].y = 0;
            forces[i].z = 0;
        }

        // Compute repulsive forces between all pairs
        // We use a high power repulsive potential to approximate hard spheres
        // Potential ~ 1/r^6 => Force ~ 1/r^7
        // Vector calculation: F_vec = direction * magnitude = (d_vec / r) * (1/r^7) = d_vec / r^8 = d_vec / (d^2)^4
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                double dx = p[i].x - p[j].x;
                double dy = p[i].y - p[j].y;
                double dz = p[i].z - p[j].z;
                double d2 = dx*dx + dy*dy + dz*dz;
                
                // Avoid division by zero
                if (d2 < 1e-10) d2 = 1e-10; 

                // Calculate force factor 1 / (d2^4)
                double d2_2 = d2 * d2;
                double factor = 1.0 / (d2_2 * d2_2); 

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

        // Find the maximum force magnitude to scale the step size
        double max_f = 0;
        for (int i = 0; i < n; ++i) {
            double f2 = forces[i].x*forces[i].x + forces[i].y*forces[i].y + forces[i].z*forces[i].z;
            if (f2 > max_f) max_f = f2;
        }
        max_f = sqrt(max_f);

        // Determine step size ensuring no point moves more than move_limit
        double current_step = alpha;
        if (max_f * current_step > move_limit) {
            current_step = move_limit / max_f;
        }

        // Update positions and project back onto the unit sphere
        for (int i = 0; i < n; ++i) {
            p[i].x += forces[i].x * current_step;
            p[i].y += forces[i].y * current_step;
            p[i].z += forces[i].z * current_step;

            double d2 = p[i].x*p[i].x + p[i].y*p[i].y + p[i].z*p[i].z;
            double inv_d = 1.0 / sqrt(d2);
            p[i].x *= inv_d;
            p[i].y *= inv_d;
            p[i].z *= inv_d;
        }
        
        // Decay the movement limit to stabilize the configuration
        move_limit *= 0.995; 
    }
    
    // Calculate the final minimum pairwise distance
    double min_dist_sq = 1e18;
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            double dx = p[i].x - p[j].x;
            double dy = p[i].y - p[j].y;
            double dz = p[i].z - p[j].z;
            double d2 = dx*dx + dy*dy + dz*dz;
            if (d2 < min_dist_sq) min_dist_sq = d2;
        }
    }

    // Output results
    cout << fixed << setprecision(9) << sqrt(min_dist_sq) << endl;
    for (int i = 0; i < n; ++i) {
        cout << p[i].x << " " << p[i].y << " " << p[i].z << endl;
    }

    return 0;
}