#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>

struct Point {
    double x, y, z;
};

// Heuristic threshold for running the simulation.
// For larger n, the simulation is too slow.
const int SIMULATION_N_THRESHOLD = 1500;
const int SIMULATION_ITERATIONS = 50;

void solve() {
    int n;
    std::cin >> n;

    if (n == 1) {
        std::cout << "0.5 0.5 0.5\n";
        return;
    }

    // Phase 1: Initial placement using FCC lattice
    std::vector<Point> centers;
    centers.reserve(n);

    int M = 0;
    if (n > 0) {
        M = static_cast<int>(ceil(pow(n / 4.0, 1.0 / 3.0)));
    }
    if (M == 0) M = 1;

    int count = 0;
    for (int i = 0; i < M && count < n; ++i) {
        for (int j = 0; j < M && count < n; ++j) {
            for (int k = 0; k < M && count < n; ++k) {
                if (count < n) centers.push_back({(double)i, (double)j, (double)k}); else break;
                count++;
                if (count < n) centers.push_back({(double)i + 0.5, (double)j + 0.5, (double)k}); else break;
                count++;
                if (count < n) centers.push_back({(double)i + 0.5, (double)j, (double)k + 0.5}); else break;
                count++;
                if (count < n) centers.push_back({(double)i, (double)j + 0.5, (double)k + 0.5}); else break;
                count++;
            }
        }
    }
    
    double r_est;
    double L;

    if (M > 1) {
        L = M - 0.5;
        r_est = 1.0 / (2.0 * (sqrt(2.0) * L + 1.0));
    } else { // M=1, for small n
        double max_coord = 0.0;
        for(const auto& p : centers) {
           max_coord = std::max({max_coord, p.x, p.y, p.z});
        }
        L = max_coord > 1e-9 ? max_coord : 1.0;
        // Re-estimate radius for this smaller point cloud
        double d_min_orig = 1e9;
        for(size_t i = 0; i < centers.size(); ++i) {
            for(size_t j = i + 1; j < centers.size(); ++j) {
                double dx = centers[i].x - centers[j].x;
                double dy = centers[i].y - centers[j].y;
                double dz = centers[i].z - centers[j].z;
                d_min_orig = std::min(d_min_orig, sqrt(dx*dx + dy*dy + dz*dz));
            }
        }
        r_est = d_min_orig / (2.0 * (L + d_min_orig));
    }

    double scale = (1.0 - 2.0 * r_est) / L;
    for (auto& p : centers) {
        p.x = r_est + p.x * scale;
        p.y = r_est + p.y * scale;
        p.z = r_est + p.z * scale;
    }

    // Phase 2: Refine positions using physics-based simulation
    if (n < SIMULATION_N_THRESHOLD) {
        double step = r_est * 0.1;

        for (int iter = 0; iter < SIMULATION_ITERATIONS; ++iter) {
            std::vector<Point> forces(n, {0, 0, 0});
            double max_force_sq = 0.0;

            for (int i = 0; i < n; ++i) {
                // Particle-particle forces from potential ~1/d^2
                for (int j = 0; j < n; ++j) {
                    if (i == j) continue;
                    double dx = centers[i].x - centers[j].x;
                    double dy = centers[i].y - centers[j].y;
                    double dz = centers[i].z - centers[j].z;
                    double dist_sq = dx * dx + dy * dy + dz * dz;
                    if (dist_sq < 1e-18) dist_sq = 1e-18;
                    double inv_dist_4 = 1.0 / (dist_sq * dist_sq);
                    forces[i].x += dx * inv_dist_4;
                    forces[i].y += dy * inv_dist_4;
                    forces[i].z += dz * inv_dist_4;
                }

                // Wall forces (coeff derived for potential ~1/(2x)^2)
                double inv_x = 1.0/centers[i].x;
                double inv_1mx = 1.0/(1.0-centers[i].x);
                forces[i].x += 0.25 * (pow(inv_x, 3) - pow(inv_1mx, 3));

                double inv_y = 1.0/centers[i].y;
                double inv_1my = 1.0/(1.0-centers[i].y);
                forces[i].y += 0.25 * (pow(inv_y, 3) - pow(inv_1my, 3));
                
                double inv_z = 1.0/centers[i].z;
                double inv_1mz = 1.0/(1.0-centers[i].z);
                forces[i].z += 0.25 * (pow(inv_z, 3) - pow(inv_1mz, 3));
            }

            for(int i = 0; i < n; ++i) {
                max_force_sq = std::max(max_force_sq, forces[i].x * forces[i].x + forces[i].y * forces[i].y + forces[i].z * forces[i].z);
            }

            double move_scale = step / sqrt(max_force_sq);
            if (std::isinf(move_scale) || std::isnan(move_scale)) move_scale = 0;
            
            for (int i = 0; i < n; ++i) {
                centers[i].x += forces[i].x * move_scale;
                centers[i].y += forces[i].y * move_scale;
                centers[i].z += forces[i].z * move_scale;

                centers[i].x = std::max(1e-9, std::min(1.0 - 1e-9, centers[i].x));
                centers[i].y = std::max(1e-9, std::min(1.0 - 1e-9, centers[i].y));
                centers[i].z = std::max(1e-9, std::min(1.0 - 1e-9, centers[i].z));
            }
            step *= 0.99;
        }
    }

    std::cout << std::fixed << std::setprecision(17);
    for (const auto& p : centers) {
        std::cout << p.x << " " << p.y << " " << p.z << "\n";
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}