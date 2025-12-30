#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <random>
#include <chrono>

using namespace std;

struct Point {
    double x, y, z;
};

// Squared Euclidean distance
double dist_sq(const Point& a, const Point& b) {
    return (a.x - b.x)*(a.x - b.x) + (a.y - b.y)*(a.y - b.y) + (a.z - b.z)*(a.z - b.z);
}

// Global N
int N;

// Generate FCC points in a minimal bounding box
// FCC lattice: integer coords (x,y,z) with x+y+z even.
vector<Point> generate_fcc(int n) {
    int L = 0;
    vector<Point> candidates;
    
    // Find minimal integer cube size L that holds >= n points
    while (true) {
        L++;
        // Rough capacity check: density is 0.5, volume L^3.
        // 0.5 * (L+1)^3 must be approx >= n.
        if (0.5 * (double)(L+1)*(L+1)*(L+1) < n) continue;
        
        candidates.clear();
        for (int x = 0; x <= L; ++x) {
            for (int y = 0; y <= L; ++y) {
                for (int z = 0; z <= L; ++z) {
                    if ((x + y + z) % 2 == 0) {
                        candidates.push_back({(double)x, (double)y, (double)z});
                    }
                }
            }
        }
        if (candidates.size() >= n) break;
    }

    // Keep the first n points. 
    // Usually these fill the box lexicographically, which is reasonably compact.
    if (candidates.size() > n) {
        candidates.resize(n);
    }
    
    // Normalize to [0, 1] preserving aspect ratio to maximize separation
    double min_x = 1e9, max_x = -1e9;
    double min_y = 1e9, max_y = -1e9;
    double min_z = 1e9, max_z = -1e9;
    
    for (auto& p : candidates) {
        if (p.x < min_x) min_x = p.x;
        if (p.x > max_x) max_x = p.x;
        if (p.y < min_y) min_y = p.y;
        if (p.y > max_y) max_y = p.y;
        if (p.z < min_z) min_z = p.z;
        if (p.z > max_z) max_z = p.z;
    }
    
    double size = max({max_x - min_x, max_y - min_y, max_z - min_z});
    if (size == 0) size = 1;

    vector<Point> result;
    for (auto& p : candidates) {
        // Map to unit cube, centering the distribution
        double nx = (p.x - min_x) / size;
        double ny = (p.y - min_y) / size;
        double nz = (p.z - min_z) / size;
        
        // Centering offsets
        double cx = (max_x - min_x) / size;
        double cy = (max_y - min_y) / size;
        double cz = (max_z - min_z) / size;
        
        nx += (1.0 - cx) * 0.5;
        ny += (1.0 - cy) * 0.5;
        nz += (1.0 - cz) * 0.5;
        
        result.push_back({nx, ny, nz});
    }
    return result;
}

// Local optimization (repulsion) to improve packing
void optimize(vector<Point>& points, double time_limit_sec) {
    int n = points.size();
    if (n < 2) return;
    
    auto start_time = chrono::steady_clock::now();
    
    // Parameters
    double step = 0.005; 
    double decay = 0.99;
    
    // Estimate interaction radius based on volume
    double est_dist = pow(1.0/n, 1.0/3.0);
    double radius = est_dist * 1.4; 
    
    // Grid setup for spatial hashing
    int grid_dim = (int)(1.0 / radius);
    if (grid_dim < 1) grid_dim = 1;
    if (grid_dim > 40) grid_dim = 40; 
    double cell_size = 1.0 / grid_dim;
    
    vector<vector<int>> grid(grid_dim * grid_dim * grid_dim);
    
    int iter = 0;
    while (true) {
        iter++;
        if (iter % 10 == 0) {
             auto curr = chrono::steady_clock::now();
             chrono::duration<double> elapsed = curr - start_time;
             if (elapsed.count() > time_limit_sec) break;
        }

        // Build grid
        for(auto &g : grid) g.clear();
        for (int i = 0; i < n; ++i) {
            int gx = min((int)(points[i].x / cell_size), grid_dim - 1);
            int gy = min((int)(points[i].y / cell_size), grid_dim - 1);
            int gz = min((int)(points[i].z / cell_size), grid_dim - 1);
            grid[gx * grid_dim * grid_dim + gy * grid_dim + gz].push_back(i);
        }
        
        // For each point, apply repulsion from neighbors
        for (int i = 0; i < n; ++i) {
            Point force = {0, 0, 0};
            
            int gx = min((int)(points[i].x / cell_size), grid_dim - 1);
            int gy = min((int)(points[i].y / cell_size), grid_dim - 1);
            int gz = min((int)(points[i].z / cell_size), grid_dim - 1);
            
            for (int dx = -1; dx <= 1; ++dx) {
                for (int dy = -1; dy <= 1; ++dy) {
                    for (int dz = -1; dz <= 1; ++dz) {
                        int nx = gx + dx;
                        int ny = gy + dy;
                        int nz = gz + dz;
                        
                        if (nx >= 0 && nx < grid_dim && ny >= 0 && ny < grid_dim && nz >= 0 && nz < grid_dim) {
                            int cell_idx = nx * grid_dim * grid_dim + ny * grid_dim + nz;
                            for (int j : grid[cell_idx]) {
                                if (i == j) continue;
                                double d2 = dist_sq(points[i], points[j]);
                                if (d2 < radius * radius && d2 > 1e-12) {
                                    double d = sqrt(d2);
                                    double f = (radius - d); 
                                    force.x += (points[i].x - points[j].x) / d * f;
                                    force.y += (points[i].y - points[j].y) / d * f;
                                    force.z += (points[i].z - points[j].z) / d * f;
                                }
                            }
                        }
                    }
                }
            }
            
            points[i].x += force.x * step;
            points[i].y += force.y * step;
            points[i].z += force.z * step;
            
            // Clamp to unit cube
            if (points[i].x < 0) points[i].x = 0;
            else if (points[i].x > 1) points[i].x = 1;
            if (points[i].y < 0) points[i].y = 0;
            else if (points[i].y > 1) points[i].y = 1;
            if (points[i].z < 0) points[i].z = 0;
            else if (points[i].z > 1) points[i].z = 1;
        }
        
        step *= decay;
        if (step < 1e-6) step = 1e-6; 
    }
}

// Generate Random Points
vector<Point> generate_random(int n) {
    vector<Point> res;
    // Use fixed seed for reproducibility locally, though not strictly required
    static mt19937 rng(12345);
    uniform_real_distribution<double> dist(0.0, 1.0);
    for(int i=0; i<n; ++i) res.push_back({dist(rng), dist(rng), dist(rng)});
    return res;
}

// Compute implied radius from normalized centers
double compute_score(const vector<Point>& p) {
    if (p.size() < 2) return 0.5;
    double min_d_sq = 1e18;
    for(size_t i=0; i<p.size(); ++i) {
        for(size_t j=i+1; j<p.size(); ++j) {
            double d = dist_sq(p[i], p[j]);
            if(d < min_d_sq) min_d_sq = d;
        }
    }
    double delta = sqrt(min_d_sq);
    // delta is the min pairwise distance in unit cube.
    // The implied radius formula: r = delta / (2 * (1 + delta))
    return delta / (2.0 * (1.0 + delta));
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    if (!(cin >> N)) return 0;

    // We generate normalized centers u_i in [0,1]^3.
    // The final coordinates will be c_i = r + (1-2r)u_i.
    vector<Point> best_points;
    double best_r = -1.0;

    // Strategy 1: FCC Lattice
    // This is generally optimal for large N.
    {
        vector<Point> p = generate_fcc(N);
        // Spend some time optimizing the lattice arrangement
        optimize(p, 0.8); 
        double r = compute_score(p);
        if (r > best_r) {
            best_r = r;
            best_points = p;
        }
    }

    // Strategy 2: Random Initialization + Optimization (Better for small N)
    if (N < 200) {
        auto start = chrono::steady_clock::now();
        while(true) {
            auto curr = chrono::steady_clock::now();
            if (chrono::duration_cast<chrono::duration<double>>(curr - start).count() > 1.0) break;
            
            vector<Point> p = generate_random(N);
            optimize(p, 0.15);
            double r = compute_score(p);
            if (r > best_r) {
                best_r = r;
                best_points = p;
            }
        }
    }

    // Final output calculation
    // Calculate precise delta from best_points
    double min_dist_u = 1e18;
    if (N > 1) {
        for(size_t i=0; i<best_points.size(); ++i) {
            for(size_t j=i+1; j<best_points.size(); ++j) {
                 double d = dist_sq(best_points[i], best_points[j]);
                 if(d < min_dist_u) min_dist_u = d;
            }
        }
        min_dist_u = sqrt(min_dist_u);
    } else {
        min_dist_u = 0; // Irrelevant for N=1
    }
    
    // For N=1, r=0.5
    double r = (N > 1) ? (min_dist_u / (2.0 * (1.0 + min_dist_u))) : 0.5;

    cout << fixed << setprecision(12);
    for (const auto& p : best_points) {
        // Transform u_i to c_i
        // If N=1, p is irrelevant, center is 0.5
        double cx, cy, cz;
        if (N == 1) {
            cx = cy = cz = 0.5;
        } else {
            cx = r + (1.0 - 2.0 * r) * p.x;
            cy = r + (1.0 - 2.0 * r) * p.y;
            cz = r + (1.0 - 2.0 * r) * p.z;
        }
        
        // Ensure strictly within [0,1]
        cx = max(0.0, min(1.0, cx));
        cy = max(0.0, min(1.0, cy));
        cz = max(0.0, min(1.0, cz));
        
        cout << cx << " " << cy << " " << cz << "\n";
    }

    return 0;
}