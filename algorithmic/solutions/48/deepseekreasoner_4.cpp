#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <random>
#include <iomanip>

using namespace std;

const double EPS = 1e-12;
const double GOLDEN = (1 + sqrt(5)) / 2;
const int MAX_ITER = 50;

// Helper function to compute distance between two points
inline double dist2(double x1, double y1, double z1, double x2, double y2, double z2) {
    double dx = x1 - x2;
    double dy = y1 - y2;
    double dz = z1 - z2;
    return dx*dx + dy*dy + dz*dz;
}

// Helper function to compute distance to cube boundary
inline double boundary_dist(double x, double y, double z) {
    return min({x, 1-x, y, 1-y, z, 1-z});
}

// Generate simple cubic lattice positions
vector<vector<double>> generate_cubic_lattice(int n) {
    vector<vector<double>> positions;
    int m = ceil(pow(n, 1.0/3.0));
    double step = 1.0 / m;
    
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < m; j++) {
            for (int k = 0; k < m; k++) {
                if (positions.size() < n) {
                    double x = (i + 0.5) * step;
                    double y = (j + 0.5) * step;
                    double z = (k + 0.5) * step;
                    positions.push_back({x, y, z});
                }
            }
        }
    }
    return positions;
}

// Generate face-centered cubic (FCC) lattice positions
vector<vector<double>> generate_fcc_lattice(int n) {
    vector<vector<double>> positions;
    int m = ceil(pow(n * 4.0, 1.0/3.0) / 2.0); // FCC has 4 points per unit cell
    double step = 1.0 / (2 * m);
    
    for (int i = 0; i < 2*m; i++) {
        for (int j = 0; j < 2*m; j++) {
            for (int k = 0; k < 2*m; k++) {
                if (positions.size() < n) {
                    // FCC lattice points: (i,j,k) and (i+0.5,j+0.5,k) etc.
                    if ((i + j + k) % 2 == 0) {
                        double x = i * step;
                        double y = j * step;
                        double z = k * step;
                        if (x <= 1.0 && y <= 1.0 && z <= 1.0) {
                            positions.push_back({x, y, z});
                        }
                    }
                    if (positions.size() < n) {
                        double x = (i + 0.5) * step;
                        double y = (j + 0.5) * step;
                        double z = k * step;
                        if (x <= 1.0 && y <= 1.0 && z <= 1.0) {
                            positions.push_back({x, y, z});
                        }
                    }
                    if (positions.size() < n) {
                        double x = (i + 0.5) * step;
                        double y = j * step;
                        double z = (k + 0.5) * step;
                        if (x <= 1.0 && y <= 1.0 && z <= 1.0) {
                            positions.push_back({x, y, z});
                        }
                    }
                    if (positions.size() < n) {
                        double x = i * step;
                        double y = (j + 0.5) * step;
                        double z = (k + 0.5) * step;
                        if (x <= 1.0 && y <= 1.0 && z <= 1.0) {
                            positions.push_back({x, y, z});
                        }
                    }
                }
            }
        }
    }
    
    // Trim to exactly n points
    if (positions.size() > n) {
        positions.resize(n);
    }
    
    return positions;
}

// Try to improve positions using repulsion
void improve_positions(vector<vector<double>>& positions, int iterations) {
    int n = positions.size();
    if (n <= 1) return;
    
    mt19937 rng(42);
    uniform_real_distribution<double> dist(-0.01, 0.01);
    
    for (int iter = 0; iter < iterations; iter++) {
        // Calculate repulsion forces
        vector<vector<double>> forces(n, {0.0, 0.0, 0.0});
        
        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                double dx = positions[j][0] - positions[i][0];
                double dy = positions[j][1] - positions[i][1];
                double dz = positions[j][2] - positions[i][2];
                double d2 = dx*dx + dy*dy + dz*dz + 1e-12;
                double force = 1.0 / (d2 * sqrt(d2));
                
                forces[i][0] -= dx * force;
                forces[i][1] -= dy * force;
                forces[i][2] -= dz * force;
                forces[j][0] += dx * force;
                forces[j][1] += dy * force;
                forces[j][2] += dz * force;
            }
        }
        
        // Apply forces with small step size
        double step = 0.01 / pow(n, 1.0/3.0);
        for (int i = 0; i < n; i++) {
            positions[i][0] += forces[i][0] * step + dist(rng);
            positions[i][1] += forces[i][1] * step + dist(rng);
            positions[i][2] += forces[i][2] * step + dist(rng);
            
            // Clamp to [0,1] cube
            positions[i][0] = max(0.0, min(1.0, positions[i][0]));
            positions[i][1] = max(0.0, min(1.0, positions[i][1]));
            positions[i][2] = max(0.0, min(1.0, positions[i][2]));
        }
    }
}

// Optimize positions using local search
void local_search(vector<vector<double>>& positions) {
    int n = positions.size();
    if (n <= 1) return;
    
    // Calculate current minimum distance
    double min_dist2 = 1e9;
    for (int i = 0; i < n; i++) {
        for (int j = i + 1; j < n; j++) {
            double d2 = dist2(positions[i][0], positions[i][1], positions[i][2],
                             positions[j][0], positions[j][1], positions[j][2]);
            min_dist2 = min(min_dist2, d2);
        }
    }
    
    // Try to improve each point
    for (int i = 0; i < n; i++) {
        double best_x = positions[i][0];
        double best_y = positions[i][1];
        double best_z = positions[i][2];
        double best_score = -1e9;
        
        // Try points around current position
        for (double dx = -0.01; dx <= 0.01; dx += 0.005) {
            for (double dy = -0.01; dy <= 0.01; dy += 0.005) {
                for (double dz = -0.01; dz <= 0.01; dz += 0.005) {
                    double x = positions[i][0] + dx;
                    double y = positions[i][1] + dy;
                    double z = positions[i][2] + dz;
                    
                    if (x < 0 || x > 1 || y < 0 || y > 1 || z < 0 || z > 1) continue;
                    
                    // Calculate minimum distance to other points
                    double current_min = 1e9;
                    for (int j = 0; j < n; j++) {
                        if (j == i) continue;
                        double d2 = dist2(x, y, z, 
                                         positions[j][0], positions[j][1], positions[j][2]);
                        current_min = min(current_min, d2);
                    }
                    
                    // Also consider distance to boundary
                    double boundary = boundary_dist(x, y, z);
                    double score = min(sqrt(current_min) / 2.0, boundary);
                    
                    if (score > best_score) {
                        best_score = score;
                        best_x = x;
                        best_y = y;
                        best_z = z;
                    }
                }
            }
        }
        
        positions[i][0] = best_x;
        positions[i][1] = best_y;
        positions[i][2] = best_z;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cin >> n;
    
    vector<vector<double>> positions;
    
    // Choose strategy based on n
    if (n <= 1000) {
        // For small n, use FCC lattice and improve
        positions = generate_fcc_lattice(n);
        improve_positions(positions, 100);
        local_search(positions);
    } else {
        // For larger n, use cubic lattice with improvement
        positions = generate_cubic_lattice(n);
        improve_positions(positions, 50);
    }
    
    // Ensure all coordinates are in [0,1]
    for (auto& p : positions) {
        p[0] = max(0.0, min(1.0, p[0]));
        p[1] = max(0.0, min(1.0, p[1]));
        p[2] = max(0.0, min(1.0, p[2]));
    }
    
    // Output with sufficient precision
    cout << fixed << setprecision(12);
    for (const auto& p : positions) {
        cout << p[0] << " " << p[1] << " " << p[2] << "\n";
    }
    
    return 0;
}