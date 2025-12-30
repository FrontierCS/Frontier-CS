#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <ctime>
#include <random>

using namespace std;

struct Point {
    double x, y, z;
};

int N;
vector<Point> p;

// Spatial Hashing
vector<int> head;
vector<int> next_node;
int grid_dim;
double cell_size;

// Rebuild the spatial grid based on the current interaction radius
void build_grid(double interaction_radius) {
    // interaction_radius is the diameter of spheres we want to separate (plus margin).
    // We need cell_size >= interaction_radius to ensure checking neighbors +/- 1 is sufficient.
    
    double target_size = interaction_radius;
    if (target_size < 1e-4) target_size = 1e-4; // Avoid division by zero/huge grid
    
    // Calculate grid dimension such that cell_size >= target_size
    grid_dim = (int)(1.0 / target_size);
    if (grid_dim < 1) grid_dim = 1;
    if (grid_dim > 64) grid_dim = 64; // Cap to avoid excessive memory usage/time
    
    cell_size = 1.0 / grid_dim;
    
    int num_cells = grid_dim * grid_dim * grid_dim;
    head.assign(num_cells, -1);
    next_node.assign(N, -1);
    
    for (int i = 0; i < N; ++i) {
        int gx = min(grid_dim - 1, max(0, (int)(p[i].x / cell_size)));
        int gy = min(grid_dim - 1, max(0, (int)(p[i].y / cell_size)));
        int gz = min(grid_dim - 1, max(0, (int)(p[i].z / cell_size)));
        int cell_idx = gx + grid_dim * (gy + grid_dim * gz);
        next_node[i] = head[cell_idx];
        head[cell_idx] = i;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    if (!(cin >> N)) return 0;
    
    // 1. Initialization using Grid Heuristic (Baseline)
    // Find m, k, l such that m*k*l >= N and max(m,k,l) is minimized.
    int best_m = 1, best_k = 1, best_l = N;
    int min_max_dim = N + 1;
    
    int limit = (int)ceil(pow(N, 1.0/3.0)) + 5;
    for (int m = 1; m <= limit; ++m) {
        for (int k = 1; k <= limit; ++k) {
            int l = (N + m*k - 1) / (m*k);
            int max_dim = max({m, k, l});
            if (max_dim < min_max_dim) {
                min_max_dim = max_dim;
                best_m = m; best_k = k; best_l = l;
            }
        }
    }
    
    p.resize(N);
    int idx = 0;
    double spacing = 1.0 / min_max_dim;
    
    // Fill the grid points
    for (int i = 0; i < best_m && idx < N; ++i) {
        for (int j = 0; j < best_k && idx < N; ++j) {
            for (int k = 0; k < best_l && idx < N; ++k) {
                p[idx].x = (i + 0.5) * spacing;
                p[idx].y = (j + 0.5) * spacing;
                p[idx].z = (k + 0.5) * spacing;
                idx++;
            }
        }
    }
    
    // Center the packing in the cube if the grid isn't cubic
    double x_span = best_m * spacing;
    double y_span = best_k * spacing;
    double z_span = best_l * spacing;
    double x_offset = (1.0 - x_span) / 2.0;
    double y_offset = (1.0 - y_span) / 2.0;
    double z_offset = (1.0 - z_span) / 2.0;
    
    for(auto& pt : p) {
        pt.x += (x_offset > 0 ? x_offset : 0);
        pt.y += (y_offset > 0 ? y_offset : 0);
        pt.z += (z_offset > 0 ? z_offset : 0);
    }

    // Add small random noise to break symmetry
    mt19937 rng(1337);
    uniform_real_distribution<double> noise(-0.0001, 0.0001);
    for(auto& pt : p) {
        pt.x += noise(rng);
        pt.y += noise(rng);
        pt.z += noise(rng);
        // Clamp to ensure valid start
        pt.x = max(0.0, min(1.0, pt.x));
        pt.y = max(0.0, min(1.0, pt.y));
        pt.z = max(0.0, min(1.0, pt.z));
    }
    
    // 2. Optimization Loop (Repulsion Simulation)
    // Start with radius estimate from grid
    double R = 0.5 / min_max_dim;
    double step_size = 0.005;
    double time_limit = 0.85; // Seconds
    clock_t start_clock = clock();
    
    int iter = 0;
    while ( (double)(clock() - start_clock) / CLOCKS_PER_SEC < time_limit ) {
        double diam = 2.0 * R;
        build_grid(diam);
        
        double max_ov = 0;
        
        // Perform multiple relaxation substeps per grid build
        for (int sub = 0; sub < 5; ++sub) {
            vector<Point> forces(N, {0,0,0});
            max_ov = 0;
            
            for (int i = 0; i < N; ++i) {
                // Wall forces: push point inwards if within radius R of wall
                double k_wall = 1.0;
                if (p[i].x < R) { forces[i].x += k_wall*(R - p[i].x); max_ov = max(max_ov, R - p[i].x); }
                if (p[i].x > 1-R) { forces[i].x -= k_wall*(p[i].x - (1-R)); max_ov = max(max_ov, p[i].x - (1-R)); }
                if (p[i].y < R) { forces[i].y += k_wall*(R - p[i].y); max_ov = max(max_ov, R - p[i].y); }
                if (p[i].y > 1-R) { forces[i].y -= k_wall*(p[i].y - (1-R)); max_ov = max(max_ov, p[i].y - (1-R)); }
                if (p[i].z < R) { forces[i].z += k_wall*(R - p[i].z); max_ov = max(max_ov, R - p[i].z); }
                if (p[i].z > 1-R) { forces[i].z -= k_wall*(p[i].z - (1-R)); max_ov = max(max_ov, p[i].z - (1-R)); }
                
                // Pair forces
                int gx = min(grid_dim - 1, max(0, (int)(p[i].x / cell_size)));
                int gy = min(grid_dim - 1, max(0, (int)(p[i].y / cell_size)));
                int gz = min(grid_dim - 1, max(0, (int)(p[i].z / cell_size)));
                
                // Check neighbor cells
                for (int dx = -1; dx <= 1; ++dx) {
                    for (int dy = -1; dy <= 1; ++dy) {
                        for (int dz = -1; dz <= 1; ++dz) {
                            int nx = gx + dx;
                            int ny = gy + dy;
                            int nz = gz + dz;
                            if (nx < 0 || nx >= grid_dim || ny < 0 || ny >= grid_dim || nz < 0 || nz >= grid_dim) continue;
                            
                            int cell = nx + grid_dim * (ny + grid_dim * nz);
                            int j = head[cell];
                            while (j != -1) {
                                if (i != j) {
                                    double dx_ij = p[i].x - p[j].x;
                                    double dy_ij = p[i].y - p[j].y;
                                    double dz_ij = p[i].z - p[j].z;
                                    
                                    // Bounding box check
                                    if (abs(dx_ij) < diam && abs(dy_ij) < diam && abs(dz_ij) < diam) {
                                        double d2 = dx_ij*dx_ij + dy_ij*dy_ij + dz_ij*dz_ij;
                                        if (d2 < diam * diam) {
                                            double d = sqrt(d2);
                                            double ov = diam - d;
                                            max_ov = max(max_ov, ov);
                                            
                                            double f = ov;
                                            if (d > 1e-9) {
                                                f /= d;
                                                forces[i].x += f * dx_ij;
                                                forces[i].y += f * dy_ij;
                                                forces[i].z += f * dz_ij;
                                            } else {
                                                // Handle exact overlap
                                                forces[i].x += f * (double)(rand()%100 - 50)/50.0;
                                                forces[i].y += f * (double)(rand()%100 - 50)/50.0;
                                                forces[i].z += f * (double)(rand()%100 - 50)/50.0;
                                            }
                                        }
                                    }
                                }
                                j = next_node[j];
                            }
                        }
                    }
                }
            }
            
            // Move points
            for (int i = 0; i < N; ++i) {
                p[i].x += step_size * forces[i].x;
                p[i].y += step_size * forces[i].y;
                p[i].z += step_size * forces[i].z;
                // Clamp to [0,1]
                p[i].x = max(0.0, min(1.0, p[i].x));
                p[i].y = max(0.0, min(1.0, p[i].y));
                p[i].z = max(0.0, min(1.0, p[i].z));
            }
        }
        
        // Dynamic Radius Adjustment:
        // If overlap is small, the current packing supports radius R, so try growing R.
        // If overlap is large, we are too ambitious, shrink R.
        if (max_ov < 1e-5 * R) {
            R *= 1.001; 
        } else {
            R *= 0.999;
        }
        
        // Decay step size slowly to converge
        if (iter > 1000) step_size = 0.002;
        if (iter > 3000) step_size = 0.001;
        
        iter++;
    }

    // Output results
    cout << fixed << setprecision(10);
    for (int i = 0; i < N; ++i) {
        cout << p[i].x << " " << p[i].y << " " << p[i].z << "\n";
    }

    return 0;
}