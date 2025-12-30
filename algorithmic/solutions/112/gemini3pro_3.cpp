#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <ctime>
#include <random>

using namespace std;

// Constants
const double PI = 3.14159265358979323846;

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

// Get the minimum pairwise distance in the set
double get_min_dist(const vector<Point>& p) {
    if (p.size() < 2) return 0.0;
    double min_d2 = 1e18;
    for (size_t i = 0; i < p.size(); ++i) {
        for (size_t j = i + 1; j < p.size(); ++j) {
            double d2 = distSq(p[i], p[j]);
            if (d2 < min_d2) min_d2 = d2;
        }
    }
    return sqrt(min_d2);
}

// Optimization routine
// mode 0: surface constrained (points projected to sphere)
// mode 1: volume constrained (points clamped to ball)
void optimize(vector<Point>& p, int mode, double duration) {
    int n = p.size();
    if (n < 2) return;
    
    clock_t start = clock();
    double init_lr = (mode == 0) ? 0.05 : 0.02;
    
    // Temporary force storage
    vector<Point> forces(n);
    
    while ((double)(clock() - start) / CLOCKS_PER_SEC < duration) {
        double progress = ((double)(clock() - start) / CLOCKS_PER_SEC) / duration;
        double lr = init_lr * (1.0 - progress);
        if (lr < 1e-4) lr = 1e-4;

        // Reset forces
        for(int i=0; i<n; ++i) forces[i] = {0, 0, 0};

        // Compute repulsive forces
        // For efficiency, we use raw loops. 
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                double dx = p[i].x - p[j].x;
                double dy = p[i].y - p[j].y;
                double dz = p[i].z - p[j].z;
                double d2 = dx*dx + dy*dy + dz*dz;
                
                // Avoid division by zero
                if (d2 < 1e-12) d2 = 1e-12;
                
                double factor = 0;
                // Force calculation
                // mode 0 (Surface): Soft repulsion (Coulomb-like 1/r^2 force) to spread points on sphere.
                // mode 1 (Volume): Harder repulsion (1/r^6 force) to pack "hard spheres" in volume.
                
                double d = sqrt(d2);
                
                if (mode == 0) {
                    // Force ~ 1/r^2 => vector factor 1/r^3
                    factor = lr / (d2 * d);
                } else {
                    // Force ~ 1/r^6 => vector factor 1/r^7
                    // d^7 = (d^2)^3 * d
                    double d6 = d2 * d2 * d2;
                    factor = lr / (d6 * d);
                }

                // Cap the force magnitude to prevent numerical explosion
                if (factor > 0.1) factor = 0.1;

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

        // Apply forces and enforce constraints
        for (int i = 0; i < n; ++i) {
            p[i].x += forces[i].x;
            p[i].y += forces[i].y;
            p[i].z += forces[i].z;
            
            double d2 = p[i].x*p[i].x + p[i].y*p[i].y + p[i].z*p[i].z;
            if (mode == 0) {
                // Surface constraint: normalize to 1
                if (d2 < 1e-12) {
                    // If at origin, push to random surface point
                    p[i].x = 1.0; p[i].y = 0.0; p[i].z = 0.0; 
                } else {
                    double inv_d = 1.0 / sqrt(d2);
                    p[i].x *= inv_d;
                    p[i].y *= inv_d;
                    p[i].z *= inv_d;
                }
            } else {
                // Volume constraint: keep inside unit sphere
                if (d2 > 1.0) {
                    double inv_d = 1.0 / sqrt(d2);
                    p[i].x *= inv_d;
                    p[i].y *= inv_d;
                    p[i].z *= inv_d;
                }
            }
        }
    }
}

// Initialize points on a Fibonacci sphere (good for surface packing)
vector<Point> init_fibonacci(int n) {
    vector<Point> p(n);
    double ga = PI * (3.0 - sqrt(5.0));
    for (int i = 0; i < n; ++i) {
        double z = 1.0 - (2.0*i + 1.0)/n;
        double radius = sqrt(max(0.0, 1.0 - z*z));
        double theta = ga * i;
        p[i].x = radius * cos(theta);
        p[i].y = radius * sin(theta);
        p[i].z = z;
    }
    return p;
}

// Initialize points using an FCC lattice (good for volume packing)
vector<Point> init_fcc(int n) {
    vector<Point> candidates;
    int L = 1;
    // Find enough lattice points
    while (true) {
        candidates.clear();
        for (int x = -L; x <= L; ++x) {
            for (int y = -L; y <= L; ++y) {
                for (int z = -L; z <= L; ++z) {
                    // FCC condition: x+y+z is even (assuming integer coords)
                    if ((x + y + z) % 2 == 0) {
                        candidates.push_back({(double)x, (double)y, (double)z});
                    }
                }
            }
        }
        if ((int)candidates.size() >= n) break;
        L++;
    }
    
    // Sort by distance from origin to pack centrally
    sort(candidates.begin(), candidates.end(), [](const Point& a, const Point& b){
        return (a.x*a.x+a.y*a.y+a.z*a.z) < (b.x*b.x+b.y*b.y+b.z*b.z);
    });
    
    // Select n points
    vector<Point> p(n);
    double max_d = 0;
    for(int i=0; i<n; ++i) {
        p[i] = candidates[i];
        // Add tiny noise to break perfect symmetry in degenerate cases
        p[i].x += (rand() % 1000) * 1e-6;
        p[i].y += (rand() % 1000) * 1e-6;
        p[i].z += (rand() % 1000) * 1e-6;
        max_d = max(max_d, sqrt(p[i].x*p[i].x + p[i].y*p[i].y + p[i].z*p[i].z));
    }
    
    // Scale to fit in unit sphere
    if (max_d < 1e-9) max_d = 1.0; 
    for(int i=0; i<n; ++i) {
        p[i].x /= max_d;
        p[i].y /= max_d;
        p[i].z /= max_d;
    }
    return p;
}

int main() {
    // Fast IO
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    srand(time(NULL));

    // Strategy 1: Surface Optimization
    // Initialize with Fibonacci spiral and relax
    vector<Point> p1 = init_fibonacci(n);
    // Allocate ~0.9 seconds to this strategy
    optimize(p1, 0, 0.9);
    double d1 = get_min_dist(p1);

    // Strategy 2: Volume Optimization
    // Initialize with FCC lattice and relax with hard-sphere repulsion
    vector<Point> p2 = init_fcc(n);
    // Allocate ~0.9 seconds to this strategy
    optimize(p2, 1, 0.9);
    double d2 = get_min_dist(p2);

    // Choose the best configuration
    vector<Point> final_p;
    double final_d;

    if (d1 >= d2) {
        final_p = p1;
        final_d = d1;
    } else {
        final_p = p2;
        final_d = d2;
    }

    // Output
    cout << fixed << setprecision(9) << final_d << endl;
    for (const auto& pt : final_p) {
        cout << pt.x << " " << pt.y << " " << pt.z << endl;
    }

    return 0;
}