#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <random>
#include <iomanip>
#include <chrono>

using namespace std;

struct Point {
    double x, y, z;
};

int N;
vector<Point> best_solution;
double best_r = -1.0;

// Helper to compute squared distance
inline double distSq(const Point& a, const Point& b) {
    double dx = a.x - b.x;
    double dy = a.y - b.y;
    double dz = a.z - b.z;
    return dx*dx + dy*dy + dz*dz;
}

// Compute the score (radius) of a configuration
// This runs in O(N^2) but is only called a few times.
double compute_radius(const vector<Point>& p) {
    if (p.empty()) return 0.0;
    double min_d2 = 1e18;
    for (size_t i = 0; i < p.size(); ++i) {
        for (size_t j = i + 1; j < p.size(); ++j) {
            min_d2 = min(min_d2, distSq(p[i], p[j]));
        }
    }
    double r_pair = sqrt(min_d2) / 2.0;
    
    double min_wall = 1e18;
    for (const auto& pt : p) {
        min_wall = min(min_wall, pt.x);
        min_wall = min(min_wall, 1.0 - pt.x);
        min_wall = min(min_wall, pt.y);
        min_wall = min(min_wall, 1.0 - pt.y);
        min_wall = min(min_wall, pt.z);
        min_wall = min(min_wall, 1.0 - pt.z);
    }
    return min(r_pair, min_wall);
}

// Grid for O(N) neighbor search
struct Grid {
    double cell_size;
    int dims;
    vector<vector<int>> cells;
    
    void setup(double radius_guess) {
        // Cell size should be comparable to diameter (2*radius)
        // Ensure at least minimal size and not too huge grid
        cell_size = max(radius_guess * 2.0, 1e-4); 
        dims = max(1, (int)(1.0 / cell_size));
        // Recalculate cell_size to match dims exactly for [0,1)
        cell_size = 1.0 / dims; 
        int total_cells = dims * dims * dims;
        if (cells.size() != total_cells) {
            cells.assign(total_cells, vector<int>());
        } else {
            for(auto &c : cells) c.clear();
        }
    }

    void clear() {
        for(auto &c : cells) c.clear();
    }

    void insert(int idx, const Point& p) {
        int cx = min(dims - 1, max(0, (int)(p.x / cell_size)));
        int cy = min(dims - 1, max(0, (int)(p.y / cell_size)));
        int cz = min(dims - 1, max(0, (int)(p.z / cell_size)));
        cells[cx + cy * dims + cz * dims * dims].push_back(idx);
    }
    
    void get_neighbors(int idx, const Point& p, vector<int>& neighbors) {
        int cx = min(dims - 1, max(0, (int)(p.x / cell_size)));
        int cy = min(dims - 1, max(0, (int)(p.y / cell_size)));
        int cz = min(dims - 1, max(0, (int)(p.z / cell_size)));
        
        for (int dx = -1; dx <= 1; ++dx) {
            for (int dy = -1; dy <= 1; ++dy) {
                for (int dz = -1; dz <= 1; ++dz) {
                    int nx = cx + dx;
                    int ny = cy + dy;
                    int nz = cz + dz;
                    if (nx >= 0 && nx < dims && ny >= 0 && ny < dims && nz >= 0 && nz < dims) {
                        const auto& cell_pts = cells[nx + ny * dims + nz * dims * dims];
                        for (int other : cell_pts) {
                            if (other != idx) neighbors.push_back(other);
                        }
                    }
                }
            }
        }
    }
};

void optimize(vector<Point>& p, int max_iters, double start_r) {
    double current_diam = start_r * 2.0;
    double target_diam = current_diam;
    
    Grid grid;
    // Initial setup
    grid.setup(start_r);

    double step_size = 0.05; 
    vector<int> neighbors;
    neighbors.reserve(200);
    vector<Point> disp(N);

    for (int iter = 0; iter < max_iters; ++iter) {
        // Dynamically adjust grid if diameter changes significantly, but usually fixed is ok
        // For correctness with growing target_diam, we re-setup periodically or if target_diam grows past cell_size
        if (target_diam > grid.cell_size) {
            grid.setup(target_diam / 2.0);
        }
        
        grid.clear();
        for (int i = 0; i < N; ++i) grid.insert(i, p[i]);
        
        double max_overlap = 0.0;
        fill(disp.begin(), disp.end(), Point{0,0,0});
        
        double target_sq = target_diam * target_diam;

        for (int i = 0; i < N; ++i) {
            neighbors.clear();
            grid.get_neighbors(i, p[i], neighbors);
            
            for (int j : neighbors) {
                double dx = p[i].x - p[j].x;
                double dy = p[i].y - p[j].y;
                double dz = p[i].z - p[j].z;
                double d2 = dx*dx + dy*dy + dz*dz;
                
                if (d2 < target_sq) {
                    double d = sqrt(d2);
                    double overlap = target_diam - d;
                    max_overlap = max(max_overlap, overlap);
                    
                    double f;
                    if (d > 1e-9) {
                        f = overlap; 
                        dx /= d; dy /= d; dz /= d;
                    } else {
                        // random kick
                        dx = ((double)rand() / RAND_MAX) - 0.5;
                        dy = ((double)rand() / RAND_MAX) - 0.5;
                        dz = ((double)rand() / RAND_MAX) - 0.5;
                        f = target_diam; 
                    }
                    disp[i].x += dx * f;
                    disp[i].y += dy * f;
                    disp[i].z += dz * f;
                }
            }
            
            // Wall repulsion
            double r_target = target_diam / 2.0;
            auto check_wall = [&](double val, double& d_comp, double sign) {
                if (sign > 0) { // wall at 0
                    if (val < r_target) {
                        double overlap = r_target - val;
                        max_overlap = max(max_overlap, overlap);
                        d_comp += overlap; 
                    }
                } else { // wall at 1
                    if (val > 1.0 - r_target) {
                        double overlap = val - (1.0 - r_target);
                        max_overlap = max(max_overlap, overlap);
                        d_comp -= overlap;
                    }
                }
            };
            
            check_wall(p[i].x, disp[i].x, 1);
            check_wall(p[i].x, disp[i].x, -1);
            check_wall(p[i].y, disp[i].y, 1);
            check_wall(p[i].y, disp[i].y, -1);
            check_wall(p[i].z, disp[i].z, 1);
            check_wall(p[i].z, disp[i].z, -1);
        }
        
        for (int i = 0; i < N; ++i) {
            p[i].x += disp[i].x * step_size;
            p[i].y += disp[i].y * step_size;
            p[i].z += disp[i].z * step_size;
            
            p[i].x = max(0.0, min(1.0, p[i].x));
            p[i].y = max(0.0, min(1.0, p[i].y));
            p[i].z = max(0.0, min(1.0, p[i].z));
        }
        
        if (max_overlap < 1e-4 * target_diam) {
            target_diam *= 1.002;
        }
        
        // Decay step size slightly
        step_size = max(0.005, step_size * 0.999);
    }
}

// Generate FCC lattice points
vector<Point> generate_fcc(int n) {
    vector<Point> pts;
    // Estimate spacing based on density
    // FCC density ~ 0.74, but boundaries reduce efficiency.
    // Try to fill slightly more than N points and pick best.
    double s = pow(4.0 / n, 1.0/3.0);
    s *= 0.95; // Slightly denser
    
    int k = (int)(1.0 / s) + 3; 
    
    for (int x = 0; x < k; ++x) {
        for (int y = 0; y < k; ++y) {
            for (int z = 0; z < k; ++z) {
                double bx = x * s;
                double by = y * s;
                double bz = z * s;
                auto add = [&](double dx, double dy, double dz) {
                   Point p = {bx + dx*s, by + dy*s, bz + dz*s};
                   if (p.x >= 0 && p.x <= 1 && p.y >= 0 && p.y <= 1 && p.z >= 0 && p.z <= 1) {
                       pts.push_back(p);
                   }
                };
                add(0, 0, 0);
                add(0.5, 0.5, 0);
                add(0.5, 0, 0.5);
                add(0, 0.5, 0.5);
            }
        }
    }
    
    // Sort by distance to center to pick a "spherical" chunk, then scale
    // Actually, for a cube container, sorting by distance to center is not always optimal,
    // but it preserves the lattice structure better than random cropping.
    // Better: keep points closest to center.
    if (pts.size() > n) {
        sort(pts.begin(), pts.end(), [](const Point& a, const Point& b){
            double da = (a.x-0.5)*(a.x-0.5) + (a.y-0.5)*(a.y-0.5) + (a.z-0.5)*(a.z-0.5);
            double db = (b.x-0.5)*(b.x-0.5) + (b.y-0.5)*(b.y-0.5) + (b.z-0.5)*(b.z-0.5);
            return da < db;
        });
        pts.resize(n);
    } 
    else while(pts.size() < n) {
        pts.push_back({(double)rand()/RAND_MAX, (double)rand()/RAND_MAX, (double)rand()/RAND_MAX});
    }
    
    // Initial scaling to fill box
    double min_x=1, max_x=0, min_y=1, max_y=0, min_z=1, max_z=0;
    for(auto& p : pts) {
        min_x = min(min_x, p.x); max_x = max(max_x, p.x);
        min_y = min(min_y, p.y); max_y = max(max_y, p.y);
        min_z = min(min_z, p.z); max_z = max(max_z, p.z);
    }
    double cx = (min_x + max_x) / 2.0;
    double cy = (min_y + max_y) / 2.0;
    double cz = (min_z + max_z) / 2.0;
    double range = max({max_x - min_x, max_y - min_y, max_z - min_z, 1e-9});
    double scale = 0.99 / range;
    
    for(auto& p : pts) {
        p.x = 0.5 + (p.x - cx) * scale;
        p.y = 0.5 + (p.y - cy) * scale;
        p.z = 0.5 + (p.z - cz) * scale;
        p.x = max(0.0, min(1.0, p.x));
        p.y = max(0.0, min(1.0, p.y));
        p.z = max(0.0, min(1.0, p.z));
    }
    return pts;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    if (!(cin >> N)) return 0;
    
    srand(12345);

    int attempts = 1;
    int iterations = 2000;
    
    if (N <= 200) {
        attempts = 20; 
        iterations = 5000;
    } else if (N <= 1000) {
        attempts = 3;
        iterations = 3000;
    } else {
        attempts = 1;
        iterations = 1500;
    }
    
    auto update_best = [&](const vector<Point>& current) {
        double r = compute_radius(current);
        if (r > best_r) {
            best_r = r;
            best_solution = current;
        }
    };

    // 1. Lattice initialization
    {
        vector<Point> pts = generate_fcc(N);
        double est_r = pow(0.74 / (N * 4.0/3.0 * 3.14159), 1.0/3.0); 
        optimize(pts, iterations, est_r);
        update_best(pts);
    }
    
    // 2. Random initializations (for smaller N)
    if (N <= 500) {
        for (int a = 0; a < attempts; ++a) {
            vector<Point> pts(N);
            for(int i=0; i<N; ++i) {
                pts[i] = {(double)rand()/RAND_MAX, (double)rand()/RAND_MAX, (double)rand()/RAND_MAX};
            }
            double est_r = pow(0.5 / N, 1.0/3.0) * 0.5;
            optimize(pts, iterations, est_r);
            update_best(pts);
        }
    }

    cout << fixed << setprecision(10);
    for (const auto& p : best_solution) {
        cout << p.x << " " << p.y << " " << p.z << "\n";
    }

    return 0;
}