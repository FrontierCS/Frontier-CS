#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <ctime>
#include <iomanip>
#include <random>

using namespace std;

// Define a point structure
struct Point {
    double x, y, z;
};

// Calculate squared Euclidean distance
double distSq(const Point& a, const Point& b) {
    double dx = a.x - b.x;
    double dy = a.y - b.y;
    double dz = a.z - b.z;
    return dx*dx + dy*dy + dz*dz;
}

// Calculate the minimum pairwise distance in the set
double get_min_dist(const vector<Point>& pts) {
    double min_d2 = 1e18;
    for (size_t i = 0; i < pts.size(); ++i) {
        for (size_t j = i + 1; j < pts.size(); ++j) {
            double d2 = distSq(pts[i], pts[j]);
            if (d2 < min_d2) min_d2 = d2;
        }
    }
    return sqrt(min_d2);
}

void solve() {
    int N;
    if (!(cin >> N)) return;

    // Time management
    clock_t start_time = clock();
    double time_limit = 1.85; // Safety margin within 2.0s

    vector<Point> best_pts;
    double max_min_dist = -1.0;

    auto update_best = [&](vector<Point>& current_pts) {
        double current_min = get_min_dist(current_pts);
        if (current_min > max_min_dist) {
            max_min_dist = current_min;
            best_pts = current_pts;
        }
    };

    // Precompute Fibonacci Sphere points
    // This provides a very good, nearly uniform initial configuration.
    vector<Point> fib_pts(N);
    double offset = 2.0 / N;
    double increment = M_PI * (3.0 - sqrt(5.0));
    for (int i = 0; i < N; ++i) {
        double y = ((i * offset) - 1) + (offset / 2);
        double r = sqrt(max(0.0, 1.0 - y * y));
        double phi = i * increment;
        fib_pts[i] = {cos(phi) * r, y, sin(phi) * r};
    }

    // Random number generator for restarts
    mt19937 rng(1337);
    uniform_real_distribution<double> dist_uni(-1.0, 1.0);

    // Reusable vector for forces
    vector<Point> forces(N);
    
    int attempt = 0;
    while (true) {
        // Check time at the start of attempt
        if ((double)(clock() - start_time) / CLOCKS_PER_SEC > time_limit) break;

        vector<Point> pts(N);
        if (attempt == 0) {
            pts = fib_pts;
        } else {
            // Random initialization
            for (int i = 0; i < N; ++i) {
                double x, y, z, d2;
                do {
                    x = dist_uni(rng);
                    y = dist_uni(rng);
                    z = dist_uni(rng);
                    d2 = x*x + y*y + z*z;
                } while (d2 > 1.0 || d2 < 1e-9);
                double d = sqrt(d2);
                pts[i] = {x/d, y/d, z/d};
            }
        }

        // Optimization parameters
        double lr, lr_decay;
        int max_iter;
        
        // Adjust parameters based on N to balance quality and speed
        if (N < 100) {
            lr = 0.1;
            lr_decay = 0.98;
            max_iter = 1000;
        } else {
            lr = 0.05;
            lr_decay = 0.995;
            max_iter = 2000;
        }

        for (int iter = 0; iter < max_iter; ++iter) {
            // Check time periodically
            if ((iter & 63) == 0) {
                if ((double)(clock() - start_time) / CLOCKS_PER_SEC > time_limit) break;
            }

            // Reset forces
            for(int k=0; k<N; ++k) forces[k] = {0,0,0};

            // Compute repulsive forces between all pairs
            // We use a "soft" repulsion that becomes steeper for closer points.
            // Force vector proportional to displacement * (1/d^6) roughly approximates
            // maximizing the minimum distance (Tammes problem).
            for (int i = 0; i < N; ++i) {
                for (int j = i + 1; j < N; ++j) {
                    double dx = pts[i].x - pts[j].x;
                    double dy = pts[i].y - pts[j].y;
                    double dz = pts[i].z - pts[j].z;
                    double d2 = dx*dx + dy*dy + dz*dz;
                    
                    if (d2 < 1e-12) d2 = 1e-12; // Avoid division by zero

                    // We use 1/d^6 factor for force vector.
                    // This corresponds to a force magnitude of 1/d^5.
                    double d6 = d2 * d2 * d2;
                    double factor = 1.0 / d6;

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

            // Apply forces and project back to sphere
            for (int i = 0; i < N; ++i) {
                pts[i].x += forces[i].x * lr;
                pts[i].y += forces[i].y * lr;
                pts[i].z += forces[i].z * lr;

                double mag = sqrt(pts[i].x*pts[i].x + pts[i].y*pts[i].y + pts[i].z*pts[i].z);
                if (mag > 1e-12) {
                    pts[i].x /= mag;
                    pts[i].y /= mag;
                    pts[i].z /= mag;
                } else {
                    // Degenerate case, reset to random unit vector
                    pts[i] = {1.0, 0.0, 0.0}; 
                }
            }

            lr *= lr_decay;
            if (lr < 1e-7) break;
        }

        update_best(pts);
        attempt++;
    }

    // Output results
    cout << fixed << setprecision(9) << max_min_dist << "\n";
    for (const auto& p : best_pts) {
        cout << p.x << " " << p.y << " " << p.z << "\n";
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}