#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <random>
#include <chrono>

using namespace std;

// Constants and Types
typedef double Real;
struct Point {
    Real x, y, z;
};

// Distance squared
Real distSq(const Point& a, const Point& b) {
    return (a.x - b.x)*(a.x - b.x) + (a.y - b.y)*(a.y - b.y) + (a.z - b.z)*(a.z - b.z);
}

// Global best solution
vector<Point> best_centers;
Real best_r = -1.0;

// Update global best if current is better
void update_best(const vector<Point>& centers) {
    if (centers.empty()) return;
    int n = centers.size();
    Real min_d2 = 1e18;
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            min_d2 = min(min_d2, distSq(centers[i], centers[j]));
        }
    }
    Real r_sep = sqrt(min_d2) / 2.0;
    Real min_wall = 1e18;
    for (const auto& p : centers) {
        min_wall = min(min_wall, p.x);
        min_wall = min(min_wall, 1.0 - p.x);
        min_wall = min(min_wall, p.y);
        min_wall = min(min_wall, 1.0 - p.y);
        min_wall = min(min_wall, p.z);
        min_wall = min(min_wall, 1.0 - p.z);
    }
    Real r_curr = min(r_sep, min_wall);
    
    if (r_curr > best_r) {
        best_r = r_curr;
        best_centers = centers;
    }
}

// Function to calculate radius for a set of raw points (not scaled to unit cube yet)
// Returns the max radius achievable in unit cube by scaling
// Also returns the scaled points
pair<Real, vector<Point>> fit_to_cube(const vector<Point>& raw_points) {
    if (raw_points.empty()) return {0.0, {}};
    Real min_x = 1e18, max_x = -1e18;
    Real min_y = 1e18, max_y = -1e18;
    Real min_z = 1e18, max_z = -1e18;
    
    for (const auto& p : raw_points) {
        min_x = min(min_x, p.x); max_x = max(max_x, p.x);
        min_y = min(min_y, p.y); max_y = max(max_y, p.y);
        min_z = min(min_z, p.z); max_z = max(max_z, p.z);
    }
    
    Real Lx = max_x - min_x;
    Real Ly = max_y - min_y;
    Real Lz = max_z - min_z;
    Real L_box = max({Lx, Ly, Lz});
    
    // Find min separation in raw coords
    Real min_dist_raw = 1e18;
    for (size_t i = 0; i < raw_points.size(); ++i) {
        for (size_t j = i + 1; j < raw_points.size(); ++j) {
            min_dist_raw = min(min_dist_raw, distSq(raw_points[i], raw_points[j]));
        }
    }
    min_dist_raw = sqrt(min_dist_raw);
    
    // Formula: r = 1 / (2 * (L/D + 1))
    // If min_dist_raw is 0 (duplicate points), r is 0.
    if (min_dist_raw < 1e-12) return {0.0, raw_points};

    Real r = 1.0 / (2.0 * (L_box / min_dist_raw + 1.0));
    Real s = 2.0 * r / min_dist_raw;
    
    vector<Point> final_points;
    final_points.reserve(raw_points.size());
    
    // Center the bounding box in the available space [r, 1-r]
    // Available space width: 1-2r
    // Used space width: s * Lx
    Real offset_x = r + ((1.0 - 2.0*r) - s * Lx) / 2.0;
    Real offset_y = r + ((1.0 - 2.0*r) - s * Ly) / 2.0;
    Real offset_z = r + ((1.0 - 2.0*r) - s * Lz) / 2.0;
    
    for (const auto& p : raw_points) {
        final_points.push_back({
            (p.x - min_x) * s + offset_x,
            (p.y - min_y) * s + offset_y,
            (p.z - min_z) * s + offset_z
        });
    }
    return {r, final_points};
}

// --- Optimization ---
// Simple gradient descent / relaxation maximizing min distance
void optimize(vector<Point>& points, int max_iter) {
    int n = points.size();
    if (n < 2) return;
    
    for (int iter = 0; iter < max_iter; ++iter) {
        // Find current worst constraints
        double min_d2 = 1e18;
        for(int i=0; i<n; ++i) {
            for(int j=i+1; j<n; ++j) {
                double d2 = distSq(points[i], points[j]);
                if(d2 < min_d2) min_d2 = d2;
            }
        }
        double current_sep = sqrt(min_d2);
        
        // Define a target separation slightly larger
        double target_sep = current_sep * 1.01; 
        double target_r = target_sep / 2.0;
        
        vector<Point> disp(n, {0,0,0});
        
        // Pair forces
        for(int i=0; i<n; ++i) {
            for(int j=i+1; j<n; ++j) {
                double dx = points[i].x - points[j].x;
                double dy = points[i].y - points[j].y;
                double dz = points[i].z - points[j].z;
                double d2 = dx*dx + dy*dy + dz*dz;
                
                if (d2 < target_sep*target_sep) {
                    double d = sqrt(d2);
                    double f = 0.5 * (target_sep - d) / (d + 1e-9);
                    
                    disp[i].x += dx * f;
                    disp[i].y += dy * f;
                    disp[i].z += dz * f;
                    
                    disp[j].x -= dx * f;
                    disp[j].y -= dy * f;
                    disp[j].z -= dz * f;
                }
            }
        }
        
        // Wall forces
        for(int i=0; i<n; ++i) {
            if (points[i].x < target_r) disp[i].x += (target_r - points[i].x);
            if (points[i].x > 1 - target_r) disp[i].x -= (points[i].x - (1 - target_r));
            
            if (points[i].y < target_r) disp[i].y += (target_r - points[i].y);
            if (points[i].y > 1 - target_r) disp[i].y -= (points[i].y - (1 - target_r));
            
            if (points[i].z < target_r) disp[i].z += (target_r - points[i].z);
            if (points[i].z > 1 - target_r) disp[i].z -= (points[i].z - (1 - target_r));
        }
        
        // Apply
        double move_scale = 0.5;
        for(int i=0; i<n; ++i) {
            points[i].x += disp[i].x * move_scale;
            points[i].y += disp[i].y * move_scale;
            points[i].z += disp[i].z * move_scale;
            
            points[i].x = max(0.0, min(1.0, points[i].x));
            points[i].y = max(0.0, min(1.0, points[i].y));
            points[i].z = max(0.0, min(1.0, points[i].z));
        }
    }
    update_best(points);
}


// --- Lattices ---

// 1. FCC Lattice
// Points (x,y,z) integers with x+y+z even.
void search_fcc(int n) {
    int L_est = round(pow(2.0*n, 1.0/3.0));
    
    int search_rad = 3;
    int min_L = max(1, L_est - search_rad);
    int max_L = L_est + search_rad;
    
    for (int Lx = min_L; Lx <= max_L; ++Lx) {
        for (int Ly = min_L; Ly <= max_L; ++Ly) {
            int layer_cnt = (Lx+1)*(Ly+1)/2;
            int Lz_est = (n / (max(1, layer_cnt))) * 2 + 2;
            
            for (int Lz = max(0, Lz_est - 4); Lz <= Lz_est + 4; ++Lz) {
                vector<Point> pts;
                pts.reserve(n + 100);
                for (int z = 0; z <= Lz; ++z) {
                    for (int y = 0; y <= Ly; ++y) {
                        for (int x = 0; x <= Lx; ++x) {
                            if ((x + y + z) % 2 == 0) {
                                pts.push_back({(double)x, (double)y, (double)z});
                            }
                        }
                    }
                }
                
                if (pts.size() >= n) {
                    Point center = {(double)Lx/2.0, (double)Ly/2.0, (double)Lz/2.0};
                    if (pts.size() > n) {
                        nth_element(pts.begin(), pts.begin() + n, pts.end(), 
                            [&](const Point& a, const Point& b) {
                                return distSq(a, center) < distSq(b, center);
                            });
                        pts.resize(n);
                    }
                    
                    auto res = fit_to_cube(pts);
                    if (res.first > best_r) {
                        best_r = res.first;
                        best_centers = res.second;
                    }
                }
            }
        }
    }
}

// 2. HCP Lattice
void search_hcp(int n) {
    int N_est = round(pow(n, 1.0/3.0));
    int min_d = max(1, N_est - 4);
    int max_d = N_est + 4;
    
    for (int nz = min_d; nz <= max_d; ++nz) {
        for (int ny = min_d; ny <= max_d; ++ny) {
             int nx = n / (nz * ny);
             if (nx < 1) nx = 1;
             
             for (int x_cnt = max(1, nx - 2); x_cnt <= nx + 3; ++x_cnt) {
                 vector<Point> pts;
                 pts.reserve(n + 100);
                 
                 for (int k = 0; k < nz; ++k) {
                     double z = k * sqrt(2.0/3.0);
                     double layer_dx = (k%2) * 0.5;
                     double layer_dy = (k%2) * (1.0 / (2.0 * sqrt(3.0)));
                     
                     for (int j = 0; j < ny; ++j) {
                         double y = j * (sqrt(3.0)/2.0) + layer_dy;
                         double row_dx = (j%2) * 0.5;
                         
                         for (int i = 0; i < x_cnt; ++i) {
                             double x = i + row_dx + layer_dx;
                             pts.push_back({x, y, z});
                         }
                     }
                 }
                 
                 if ((int)pts.size() >= n) {
                     Point center = {0,0,0};
                     for(auto& p : pts) { center.x += p.x; center.y += p.y; center.z += p.z; }
                     center.x /= pts.size(); center.y /= pts.size(); center.z /= pts.size();
                     
                     if (pts.size() > n) {
                        nth_element(pts.begin(), pts.begin() + n, pts.end(), 
                            [&](const Point& a, const Point& b) {
                                return distSq(a, center) < distSq(b, center);
                            });
                        pts.resize(n);
                     }
                     auto res = fit_to_cube(pts);
                     if (res.first > best_r) {
                         best_r = res.first;
                         best_centers = res.second;
                     }
                 }
             }
        }
    }
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    if (!(cin >> n)) return 0;
    
    // 1. Grid search lattices
    search_fcc(n);
    search_hcp(n);
    
    // 2. Optimization
    int iters = 200;
    if (n > 1000) iters = 40; // reduced for speed
    if (n < 200) iters = 1000;
    
    if (n <= 50) {
        mt19937 rng(1337);
        uniform_real_distribution<double> dist(0, 1);
        for(int t=0; t<5; ++t) {
            vector<Point> rand_pts(n);
            for(int i=0; i<n; ++i) rand_pts[i] = {dist(rng), dist(rng), dist(rng)};
            optimize(rand_pts, 1500);
        }
    }

    if (!best_centers.empty()) {
        vector<Point> current = best_centers;
        optimize(current, iters);
    }
    
    cout << fixed << setprecision(16);
    for (const auto& p : best_centers) {
        cout << p.x << " " << p.y << " " << p.z << "\n";
    }
    
    return 0;
}