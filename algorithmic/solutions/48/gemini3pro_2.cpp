#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>

using namespace std;

struct Point {
    double x, y, z;
};

int N;
vector<Point> best_solution;
double best_r = -1.0;

// Updates the global best solution if current r is better
void update_solution(const vector<Point>& p, double r) {
    if (r > best_r) {
        best_r = r;
        best_solution = p;
    }
}

// Simple Cubic Lattice
void try_sc() {
    int k = 1;
    while ((long long)k * k * k < N) k++;
    // Grid size k x k x k is the most balanced for a cube
    // But maybe k x k x (k+1) is better for specific N? 
    // For SC, minimizing the max dimension is optimal for radius.
    // The tightest bounding box of N points in a grid determines r.
    // Max dimension will be ceil(N^(1/3)) - 1.
    // Let L = ceil(N^(1/3)).
    // r = 1 / (2*L).
    
    int L = 1; 
    while (L*L*L < N) L++;
    
    // Check if we can do better with L x L x (L-1)?
    // If (L)(L)(L-1) >= N, then max dimension is still L-1 (indices 0..L-1).
    // Wait, indices are 0..L-1. Dimension is L.
    // Max index is L-1.
    // r = 1 / (2*(max_index) + 2) ?
    // In SC: centers at 0, 1, ... K. Span K. Scale s. 
    // s*K + 2r <= 1. 2r = s. => 2r(K+1) <= 1 => r = 1/(2(K+1)).
    // Here K is max coordinate index.
    // If dimensions are D1, D2, D3. Points 0..D1-1. Max index D1-1.
    // r = 1 / (2 * D_max).
    // We want to minimize D_max.
    // D_max is minimized when dimensions are balanced.
    // So L = ceil(N^(1/3)) is the dimension.
    
    // We can try to reduce one dimension if possible
    int dims[3] = {L, L, L};
    if ((long long)L * L * (L-1) >= N) dims[2] = L-1;
    if ((long long)L * (L-1) * (L-1) >= N) dims[1] = L-1;
    
    int D_max = max({dims[0], dims[1], dims[2]});
    double r = 1.0 / (2.0 * D_max);
    
    vector<Point> pts;
    pts.reserve(N);
    int c = 0;
    for (int z = 0; z < dims[2] && c < N; ++z) {
        for (int y = 0; y < dims[1] && c < N; ++y) {
            for (int x = 0; x < dims[0] && c < N; ++x) {
                pts.push_back({(double)x, (double)y, (double)z});
                c++;
            }
        }
    }
    
    // Scale and center
    // Centers map to [r, 1-r].
    // x_new = r + x * (2r) = r(2x + 1)
    for(auto& p : pts) {
        p.x = r * (2 * p.x + 1);
        p.y = r * (2 * p.y + 1);
        p.z = r * (2 * p.z + 1);
    }
    update_solution(pts, r);
}

// Face Centered Cubic
void try_fcc() {
    // Grid search for bounding box
    int K = ceil(pow(2*N, 1.0/3.0));
    int limit = K + 3;
    
    double best_S = 1e9;
    int best_A = -1, best_B = -1, best_C = -1;

    // Search for box dimensions [0, A] x [0, B] x [0, C]
    for (int A = 1; A <= limit * 2; ++A) {
        for (int B = 1; B <= A; ++B) {
            for (int C = 1; C <= B; ++C) {
                long long total = (long long)(A+1)*(B+1)*(C+1);
                long long cnt = (total + 1) / 2;
                if (cnt >= N) {
                    double span = A; // A is max since A>=B>=C
                    if (span < best_S) {
                        best_S = span;
                        best_A = A; best_B = B; best_C = C;
                    }
                }
            }
        }
    }

    if (best_A != -1) {
        vector<Point> pts;
        pts.reserve(best_A * best_B * best_C / 2 + 100);
        for(int x=0; x<=best_A; ++x) {
            for(int y=0; y<=best_B; ++y) {
                for(int z=0; z<=best_C; ++z) {
                    if ((x+y+z)%2 == 0) {
                        pts.push_back({(double)x, (double)y, (double)z});
                    }
                }
            }
        }
        
        // Pick N points
        // Sort by distance to center to possibly reduce effective span
        double cx = best_A / 2.0;
        double cy = best_B / 2.0;
        double cz = best_C / 2.0;
        sort(pts.begin(), pts.end(), [&](const Point& a, const Point& b){
            double d1 = pow(a.x-cx,2) + pow(a.y-cy,2) + pow(a.z-cz,2);
            double d2 = pow(b.x-cx,2) + pow(b.y-cy,2) + pow(b.z-cz,2);
            return d1 < d2;
        });
        
        if (pts.size() > N) pts.resize(N);
        
        // Recalculate span
        double min_x=1e9, max_x=-1e9, min_y=1e9, max_y=-1e9, min_z=1e9, max_z=-1e9;
        for(auto& p : pts) {
            if(p.x < min_x) min_x = p.x; if(p.x > max_x) max_x = p.x;
            if(p.y < min_y) min_y = p.y; if(p.y > max_y) max_y = p.y;
            if(p.z < min_z) min_z = p.z; if(p.z > max_z) max_z = p.z;
        }
        double S = max({max_x - min_x, max_y - min_y, max_z - min_z});
        
        double r = 1.0 / (sqrt(2.0)*S + 2.0);
        double scale = r * sqrt(2.0);
        
        double mid_x = (min_x + max_x) / 2.0;
        double mid_y = (min_y + max_y) / 2.0;
        double mid_z = (min_z + max_z) / 2.0;

        for(auto& p : pts) {
            p.x = 0.5 + (p.x - mid_x) * scale;
            p.y = 0.5 + (p.y - mid_y) * scale;
            p.z = 0.5 + (p.z - mid_z) * scale;
        }
        update_solution(pts, r);
    }
}

// Hexagonal Close Packing
void try_hcp() {
    int K = ceil(pow(N, 1.0/3.0)); 
    int limit = K + 5;
    
    double best_S_min = 1e9;
    int best_Nx=0, best_Ny=0, best_Nz=0;
    
    for (int nz = 1; nz <= limit*2; ++nz) {
         for (int ny = 1; ny <= limit*2; ++ny) {
             for (int nx = 1; nx <= limit*2; ++nx) {
                 long long cnt = (long long)nx * ny * nz;
                 if (cnt >= N) {
                     double sx = (nx - 1);
                     if (nz > 1) sx += 0.5; 
                     double sy = (ny - 1) * (sqrt(3.0)/2.0);
                     if (nz > 1) sy += (1.0 / sqrt(12.0));
                     double sz = (nz - 1) * sqrt(2.0/3.0);
                     
                     double S = max({sx, sy, sz});
                     if (S < best_S_min) {
                         best_S_min = S;
                         best_Nx = nx; best_Ny = ny; best_Nz = nz;
                     }
                 }
             }
         }
    }
    
    vector<Point> pts;
    pts.reserve(best_Nx * best_Ny * best_Nz);
    for(int k=0; k<best_Nz; ++k) {
        double z = k * sqrt(2.0/3.0);
        bool shift = (k % 2 != 0);
        for(int j=0; j<best_Ny; ++j) {
            double y = j * (sqrt(3.0)/2.0);
            if (shift) y += (1.0 / sqrt(12.0));
            for(int i=0; i<best_Nx; ++i) {
                double x = i;
                if (shift) x += 0.5;
                pts.push_back({x, y, z});
            }
        }
    }
    
    // Center sort
    double cx = (best_Nx-1)/2.0;
    double cy = (best_Ny-1)*(sqrt(3.0)/2.0)/2.0;
    double cz = (best_Nz-1)*sqrt(2.0/3.0)/2.0;
    sort(pts.begin(), pts.end(), [&](const Point& a, const Point& b){
        double d1 = pow(a.x-cx,2) + pow(a.y-cy,2) + pow(a.z-cz,2);
        double d2 = pow(b.x-cx,2) + pow(b.y-cy,2) + pow(b.z-cz,2);
        return d1 < d2;
    });

    if (pts.size() > N) pts.resize(N);

    double min_x=1e9, max_x=-1e9, min_y=1e9, max_y=-1e9, min_z=1e9, max_z=-1e9;
    for(auto& p : pts) {
         if(p.x < min_x) min_x = p.x; if(p.x > max_x) max_x = p.x;
         if(p.y < min_y) min_y = p.y; if(p.y > max_y) max_y = p.y;
         if(p.z < min_z) min_z = p.z; if(p.z > max_z) max_z = p.z;
    }
    double S = max({max_x - min_x, max_y - min_y, max_z - min_z});
    
    double r = 1.0 / (2.0 * (S + 1.0));
    double k = 2.0 * r;
    
    double mid_x = (min_x + max_x) / 2.0;
    double mid_y = (min_y + max_y) / 2.0;
    double mid_z = (min_z + max_z) / 2.0;
    
    for(auto& p : pts) {
         p.x = 0.5 + (p.x - mid_x) * k;
         p.y = 0.5 + (p.y - mid_y) * k;
         p.z = 0.5 + (p.z - mid_z) * k;
    }
    update_solution(pts, r);
}

double get_radius(const vector<Point>& p) {
    double min_d = 1e18;
    for (size_t i = 0; i < p.size(); ++i) {
        double dw = min({p[i].x, p[i].y, p[i].z, 1.0 - p[i].x, 1.0 - p[i].y, 1.0 - p[i].z});
        min_d = min(min_d, dw);
        for (size_t j = i + 1; j < p.size(); ++j) {
            double d2 = pow(p[i].x - p[j].x, 2) + pow(p[i].y - p[j].y, 2) + pow(p[i].z - p[j].z, 2);
            min_d = min(min_d, sqrt(d2) / 2.0);
        }
    }
    return min_d;
}

void optimize() {
    // Only run if N is small enough to afford O(N^2)
    if (N > 512) return;
    
    vector<Point> p = best_solution;
    double current_r = best_r;
    int iters = (N < 100) ? 1000 : 200;
    
    for (int iter = 0; iter < iters; ++iter) {
        double target_r = current_r * 1.002; 
        
        for(int sub=0; sub<10; ++sub) {
            for(int i=0; i<N; ++i) {
                double fx = 0, fy = 0, fz = 0;
                // Wall forces
                double d;
                d = p[i].x; if (d < target_r) fx += (target_r - d);
                d = 1-p[i].x; if (d < target_r) fx -= (target_r - d);
                d = p[i].y; if (d < target_r) fy += (target_r - d);
                d = 1-p[i].y; if (d < target_r) fy -= (target_r - d);
                d = p[i].z; if (d < target_r) fz += (target_r - d);
                d = 1-p[i].z; if (d < target_r) fz -= (target_r - d);
                
                // Pair forces
                for(int j=0; j<N; ++j) {
                    if (i==j) continue;
                    double dx = p[i].x - p[j].x;
                    double dy = p[i].y - p[j].y;
                    double dz = p[i].z - p[j].z;
                    double dist = sqrt(dx*dx + dy*dy + dz*dz);
                    if (dist < 2*target_r) {
                        double overlap = 2*target_r - dist;
                        if (dist > 1e-9) {
                            fx += (dx/dist) * overlap * 0.5;
                            fy += (dy/dist) * overlap * 0.5;
                            fz += (dz/dist) * overlap * 0.5;
                        } else {
                            fx += 1e-4; 
                        }
                    }
                }
                p[i].x += fx * 0.1;
                p[i].y += fy * 0.1;
                p[i].z += fz * 0.1;
                
                p[i].x = max(0.0, min(1.0, p[i].x));
                p[i].y = max(0.0, min(1.0, p[i].y));
                p[i].z = max(0.0, min(1.0, p[i].z));
            }
        }
        
        double valid_r = get_radius(p);
        if (valid_r > best_r) {
            best_r = valid_r;
            best_solution = p;
        }
        current_r = max(current_r, valid_r);
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    if (!(cin >> N)) return 0;
    
    try_sc();
    try_fcc();
    try_hcp();
    optimize();
    
    cout << fixed << setprecision(10);
    for(const auto& p : best_solution) {
        cout << p.x << " " << p.y << " " << p.z << "\n";
    }
    
    return 0;
}