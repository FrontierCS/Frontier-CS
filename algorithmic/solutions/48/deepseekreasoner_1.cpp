#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>

using namespace std;

// Constants
const double SQRT3 = sqrt(3.0);
const double SQRT2 = sqrt(2.0);
const double PHI = (1.0 + sqrt(5.0)) / 2.0; // Golden ratio

// Helper function to generate points in a face-centered cubic (FCC) lattice
vector<vector<double>> generateFCC(int n, double spacing, int& layers_x, int& layers_y, int& layers_z) {
    vector<vector<double>> points;
    
    // Estimate layers needed based on FCC packing density
    double density = M_PI / (3.0 * SQRT2); // FCC density
    double estimated_side = cbrt(n / density);
    layers_x = max(1, (int)ceil(estimated_side));
    layers_y = max(1, (int)ceil(estimated_side));
    layers_z = max(1, (int)ceil(estimated_side));
    
    // Generate FCC lattice points
    spacing = 1.0 / max(layers_x, max(layers_y, layers_z));
    
    for (int i = 0; i < layers_x; i++) {
        for (int j = 0; j < layers_y; j++) {
            for (int k = 0; k < layers_z; k++) {
                double x = i * spacing;
                double y = j * spacing;
                double z = k * spacing;
                
                // Add the four points of the FCC unit cell
                if (x <= 1.0 && y <= 1.0 && z <= 1.0) {
                    points.push_back({x, y, z});
                }
                
                if (x + spacing/2 <= 1.0 && y + spacing/2 <= 1.0 && z <= 1.0) {
                    points.push_back({x + spacing/2, y + spacing/2, z});
                }
                
                if (x + spacing/2 <= 1.0 && y <= 1.0 && z + spacing/2 <= 1.0) {
                    points.push_back({x + spacing/2, y, z + spacing/2});
                }
                
                if (x <= 1.0 && y + spacing/2 <= 1.0 && z + spacing/2 <= 1.0) {
                    points.push_back({x, y + spacing/2, z + spacing/2});
                }
            }
        }
    }
    
    return points;
}

// Helper function to generate points in a body-centered cubic (BCC) lattice
vector<vector<double>> generateBCC(int n, double spacing, int& layers_x, int& layers_y, int& layers_z) {
    vector<vector<double>> points;
    
    // Estimate layers needed
    double density = M_PI * SQRT3 / 8.0; // BCC density
    double estimated_side = cbrt(n / density);
    layers_x = max(1, (int)ceil(estimated_side));
    layers_y = max(1, (int)ceil(estimated_side));
    layers_z = max(1, (int)ceil(estimated_side));
    
    spacing = 1.0 / max(layers_x, max(layers_y, layers_z));
    
    for (int i = 0; i < layers_x; i++) {
        for (int j = 0; j < layers_y; j++) {
            for (int k = 0; k < layers_z; k++) {
                double x = i * spacing;
                double y = j * spacing;
                double z = k * spacing;
                
                if (x <= 1.0 && y <= 1.0 && z <= 1.0) {
                    points.push_back({x, y, z});
                }
                
                if (x + spacing/2 <= 1.0 && y + spacing/2 <= 1.0 && z + spacing/2 <= 1.0) {
                    points.push_back({x + spacing/2, y + spacing/2, z + spacing/2});
                }
            }
        }
    }
    
    return points;
}

// Helper function to generate points in a simple cubic lattice
vector<vector<double>> generateCubic(int n, double spacing, int& layers_x, int& layers_y, int& layers_z) {
    vector<vector<double>> points;
    
    // Calculate optimal grid dimensions
    layers_x = max(1, (int)ceil(cbrt(n)));
    layers_y = max(1, (int)ceil(cbrt(n)));
    layers_z = max(1, (int)ceil(cbrt(n)));
    
    // Adjust to have at least n points
    while (layers_x * layers_y * layers_z < n) {
        if (layers_x <= layers_y && layers_x <= layers_z) layers_x++;
        else if (layers_y <= layers_x && layers_y <= layers_z) layers_y++;
        else layers_z++;
    }
    
    spacing = 1.0 / max(layers_x, max(layers_y, layers_z));
    
    for (int i = 0; i < layers_x; i++) {
        for (int j = 0; j < layers_y; j++) {
            for (int k = 0; k < layers_z; k++) {
                double x = (i + 0.5) * spacing;
                double y = (j + 0.5) * spacing;
                double z = (k + 0.5) * spacing;
                
                if (x <= 1.0 && y <= 1.0 && z <= 1.0) {
                    points.push_back({x, y, z});
                }
            }
        }
    }
    
    return points;
}

// Helper function to generate points using a spiral/helix pattern (good for small n)
vector<vector<double>> generateSpiral(int n) {
    vector<vector<double>> points;
    
    double radius = 0.4;
    double height_step = 1.0 / n;
    
    for (int i = 0; i < n; i++) {
        double t = i / (double)n;
        double angle = 2.0 * M_PI * PHI * i; // Golden angle
        
        double x = 0.5 + radius * cos(angle) * sqrt(t);
        double y = 0.5 + radius * sin(angle) * sqrt(t);
        double z = 0.1 + 0.8 * t;
        
        // Ensure points are within [0,1]
        x = max(0.0, min(1.0, x));
        y = max(0.0, min(1.0, y));
        z = max(0.0, min(1.0, z));
        
        points.push_back({x, y, z});
    }
    
    return points;
}

// Helper function to generate optimized points for specific n values
vector<vector<double>> generateOptimizedForN(int n) {
    vector<vector<double>> points;
    
    // Special cases for small n
    if (n == 2) {
        return {{0.25, 0.25, 0.25}, {0.75, 0.75, 0.75}};
    }
    else if (n == 3) {
        return {{0.25, 0.25, 0.25}, {0.75, 0.75, 0.25}, {0.5, 0.5, 0.75}};
    }
    else if (n == 4) {
        return {{0.25, 0.25, 0.25}, {0.75, 0.25, 0.75}, 
                {0.25, 0.75, 0.75}, {0.75, 0.75, 0.25}};
    }
    else if (n == 5) {
        return {{0.5, 0.5, 0.5}, {0.2, 0.2, 0.2}, {0.8, 0.2, 0.2},
                {0.2, 0.8, 0.8}, {0.8, 0.8, 0.8}};
    }
    else if (n <= 20) {
        return generateSpiral(n);
    }
    
    // For larger n, use lattice-based approaches
    int layers_x, layers_y, layers_z;
    double spacing;
    
    if (n <= 100) {
        // Use BCC for moderate n
        auto bcc_points = generateBCC(n, spacing, layers_x, layers_y, layers_z);
        if (bcc_points.size() >= n) {
            bcc_points.resize(n);
            return bcc_points;
        }
    }
    
    // Use FCC for larger n (higher density)
    auto fcc_points = generateFCC(n, spacing, layers_x, layers_y, layers_z);
    if (fcc_points.size() >= n) {
        fcc_points.resize(n);
        return fcc_points;
    }
    
    // Fallback to cubic lattice
    auto cubic_points = generateCubic(n, spacing, layers_x, layers_y, layers_z);
    cubic_points.resize(n);
    return cubic_points;
}

// Simple pairwise repulsion to improve the packing (few iterations)
void improvePacking(vector<vector<double>>& points, int iterations = 10) {
    int n = points.size();
    if (n <= 1) return;
    
    double learning_rate = 0.1 / n;
    
    for (int iter = 0; iter < iterations; iter++) {
        vector<vector<double>> new_points = points;
        
        for (int i = 0; i < n; i++) {
            double fx = 0.0, fy = 0.0, fz = 0.0;
            
            // Repulsion from other points
            for (int j = 0; j < n; j++) {
                if (i == j) continue;
                
                double dx = points[i][0] - points[j][0];
                double dy = points[i][1] - points[j][1];
                double dz = points[i][2] - points[j][2];
                
                double dist_sq = dx*dx + dy*dy + dz*dz + 1e-12;
                double dist = sqrt(dist_sq);
                
                // Strong repulsion when too close
                if (dist < 0.1) {
                    double force = 0.01 / dist_sq;
                    fx += force * dx / dist;
                    fy += force * dy / dist;
                    fz += force * dz / dist;
                }
            }
            
            // Attraction to center to avoid drifting
            double cx = points[i][0] - 0.5;
            double cy = points[i][1] - 0.5;
            double cz = points[i][2] - 0.5;
            double center_dist_sq = cx*cx + cy*cy + cz*cz + 1e-12;
            
            fx -= 0.001 * cx / sqrt(center_dist_sq);
            fy -= 0.001 * cy / sqrt(center_dist_sq);
            fz -= 0.001 * cz / sqrt(center_dist_sq);
            
            // Update position
            new_points[i][0] += learning_rate * fx;
            new_points[i][1] += learning_rate * fy;
            new_points[i][2] += learning_rate * fz;
            
            // Clamp to [0,1]
            new_points[i][0] = max(0.0, min(1.0, new_points[i][0]));
            new_points[i][1] = max(0.0, min(1.0, new_points[i][1]));
            new_points[i][2] = max(0.0, min(1.0, new_points[i][2]));
        }
        
        points = new_points;
        learning_rate *= 0.9; // Reduce learning rate
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cin >> n;
    
    // Generate initial points
    auto points = generateOptimizedForN(n);
    
    // Apply a few iterations of improvement
    improvePacking(points, min(15, 2000 / max(1, n / 100)));
    
    // Output points with sufficient precision
    cout << fixed << setprecision(12);
    for (const auto& p : points) {
        cout << p[0] << " " << p[1] << " " << p[2] << "\n";
    }
    
    return 0;
}