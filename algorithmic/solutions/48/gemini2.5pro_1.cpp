#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>

// Structure to hold 3D coordinates. Using long double for precision.
struct Point3D {
    long double x, y, z;
};

// Structure to hold integer coordinates and squared distance from origin.
struct Point3D_int {
    int x, y, z;
    long long d2;
};

// Comparator for sorting integer points, primarily by distance, then coords.
bool comparePoints(const Point3D_int& a, const Point3D_int& b) {
    if (a.d2 != b.d2) {
        return a.d2 < b.d2;
    }
    if (a.x != b.x) {
        return a.x < b.x;
    }
    if (a.y != b.y) {
        return a.y < b.y;
    }
    return a.z < b.z;
}

// Global variables to store the best found solution.
long double best_r = -1.0;
std::vector<Point3D> best_centers;

// Function to update the best solution if a better one is found.
void update_best(long double r, const std::vector<Point3D>& centers) {
    if (r > best_r) {
        best_r = r;
        best_centers = centers;
    }
}

// Solver based on placing centers on a regular grid.
void solve_grid(int n) {
    int best_m = n, best_k = 1, best_l = 1;
    int best_max_dim = n;

    // Search for grid dimensions m, k, l that minimize max(m,k,l)
    // subject to m*k*l >= n.
    for (int m = 1; m <= n; ++m) {
        if (m > best_max_dim) break;
        double n_rem_d = (double)n / m;
        int n_rem = static_cast<int>(ceil(n_rem_d));
        if (n_rem <= 0) continue;
        
        int k_base = static_cast<int>(round(sqrt(n_rem)));
        // Check k values around sqrt(n/m) to find optimal pairing.
        for (int k_offset = -2; k_offset <= 2; ++k_offset) {
            int k = k_base + k_offset;
            if (k <= 0) k = 1;
            
            int l = static_cast<int>(ceil((double)n_rem / k));
            int current_max_dim = std::max({m, k, l});
            if (current_max_dim < best_max_dim) {
                best_max_dim = current_max_dim;
                best_m = m;
                best_k = k;
                best_l = l;
            }
        }
    }
    
    // Radius for a grid is determined by the largest dimension.
    long double r = 1.0L / (2.0L * best_max_dim);
    std::vector<Point3D> centers;
    centers.reserve(n);
    int count = 0;
    for (int i = 0; i < best_m && count < n; ++i) {
        for (int j = 0; j < best_k && count < n; ++j) {
            for (int p = 0; p < best_l && count < n; ++p) {
                centers.push_back({(i + 0.5L) / best_m, (j + 0.5L) / best_k, (p + 0.5L) / best_l});
                count++;
            }
        }
    }
    update_best(r, centers);
}

// Solver based on standard crystallographic lattices (SC, FCC, BCC).
void solve_lattice(int n, int type) {
    std::vector<Point3D_int> points;
    int S = 0;
    // Dynamically determine search box size S to get at least n points.
    while(points.size() < n){
        points.clear();
        S++;
        if (S > 20) break; // Safeguard for very large n

        for (int i = -S; i <= S; ++i) {
            for (int j = -S; j <= S; ++j) {
                for (int k = -S; k <= S; ++k) {
                    bool add = false;
                    if (type == 0) { // Simple Cubic (SC)
                        add = true;
                    } else if (type == 1) { // Face-Centered Cubic (FCC)
                        if ((i + j + k) % 2 == 0) add = true;
                    } else { // Body-Centered Cubic (BCC)
                        if (std::abs(i) % 2 == std::abs(j) % 2 && std::abs(j) % 2 == std::abs(k) % 2) add = true;
                    }
                    if (add) {
                        points.push_back({i, j, k, 1LL * i * i + 1LL * j * j + 1LL * k * k});
                    }
                }
            }
        }
    }

    std::sort(points.begin(), points.end(), comparePoints);

    std::vector<Point3D_int> chosen_points(points.begin(), points.begin() + n);

    int min_x = 1e9, max_x = -1e9;
    int min_y = 1e9, max_y = -1e9;
    int min_z = 1e9, max_z = -1e9;
    for (const auto& p : chosen_points) {
        min_x = std::min(min_x, p.x);
        max_x = std::max(max_x, p.x);
        min_y = std::min(min_y, p.y);
        max_y = std::max(max_y, p.y);
        min_z = std::min(min_z, p.z);
        max_z = std::max(max_z, p.z);
    }

    long double L = std::max({(long double)max_x - min_x, (long double)max_y - min_y, (long double)max_z - min_z});
    if (L == 0) L = 1;

    std::vector<Point3D> p_prime(n);
    for (int i = 0; i < n; ++i) {
        p_prime[i] = {
            (chosen_points[i].x - min_x) / L,
            (chosen_points[i].y - min_y) / L,
            (chosen_points[i].z - min_z) / L
        };
    }

    long double min_d2 = 1e18;
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            long double dx = p_prime[i].x - p_prime[j].x;
            long double dy = p_prime[i].y - p_prime[j].y;
            long double dz = p_prime[i].z - p_prime[j].z;
            min_d2 = std::min(min_d2, dx * dx + dy * dy + dz * dz);
        }
    }

    long double d_min_prime = sqrt(min_d2);
    long double r = d_min_prime / (2.0L * (1.0L + d_min_prime));

    std::vector<Point3D> centers(n);
    for (int i = 0; i < n; ++i) {
        centers[i] = {
            r + (1.0L - 2.0L * r) * p_prime[i].x,
            r + (1.0L - 2.0L * r) * p_prime[i].y,
            r + (1.0L - 2.0L * r) * p_prime[i].z
        };
    }
    update_best(r, centers);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    // Try multiple strategies and pick the best one.
    solve_grid(n);
    solve_lattice(n, 0); // SC
    solve_lattice(n, 1); // FCC
    solve_lattice(n, 2); // BCC
    
    std::cout << std::fixed << std::setprecision(17);
    for (const auto& center : best_centers) {
        std::cout << (double)center.x << " " << (double)center.y << " " << (double)center.z << "\n";
    }

    return 0;
}