#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <chrono>
#include <random>

// Set up fast I/O
void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

// Calculates the change in total cost if we swap the locations of facility i and facility j.
// This is an O(N) operation.
long long calculate_delta_cost(int i, int j, const std::vector<int>& p, int n,
                               const std::vector<std::vector<int>>& D,
                               const std::vector<std::vector<int>>& F) {
    if (i == j) {
        return 0;
    }

    long long delta = 0;
    int loc_i = p[i];
    int loc_j = p[j];

    for (int k = 0; k < n; ++k) {
        if (k == i || k == j) {
            continue;
        }
        int loc_k = p[k];
        // Change in cost from i's interactions with k
        delta += (long long)(D[loc_j][loc_k] - D[loc_i][loc_k]) * F[i][k];
        delta += (long long)(D[loc_k][loc_j] - D[loc_k][loc_i]) * F[k][i];
        // Change in cost from j's interactions with k
        delta += (long long)(D[loc_i][loc_k] - D[loc_j][loc_k]) * F[j][k];
        delta += (long long)(D[loc_k][loc_i] - D[loc_k][loc_j]) * F[k][j];
    }
    
    // Change in cost from interaction between i and j
    delta += (long long)(D[loc_j][loc_i] - D[loc_i][loc_j]) * F[i][j];
    delta += (long long)(D[loc_i][loc_j] - D[loc_j][loc_i]) * F[j][i];
    
    // Change in cost from self-interactions (i-i and j-j flows)
    delta += (long long)(D[loc_j][loc_j] - D[loc_i][loc_i]) * F[i][i];
    delta += (long long)(D[loc_i][loc_i] - D[loc_j][loc_j]) * F[j][j];

    return delta;
}

int main() {
    fast_io();

    int n;
    std::cin >> n;

    std::vector<std::vector<int>> D(n, std::vector<int>(n));
    std::vector<std::vector<int>> F(n, std::vector<int>(n));

    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            std::cin >> D[i][j];
        }
    }

    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            std::cin >> F[i][j];
        }
    }

    // --- Greedy Initialization ---
    std::vector<std::pair<int, int>> facility_degrees(n);
    for (int i = 0; i < n; ++i) {
        int degree = 0;
        for (int j = 0; j < n; ++j) {
            degree += F[i][j] + F[j][i];
        }
        facility_degrees[i] = {degree, i};
    }

    std::vector<std::pair<int, int>> location_degrees(n);
    for (int i = 0; i < n; ++i) {
        int degree = 0;
        for (int j = 0; j < n; ++j) {
            degree += (1 - D[i][j]) + (1 - D[j][i]);
        }
        location_degrees[i] = {degree, i};
    }

    std::sort(facility_degrees.rbegin(), facility_degrees.rend());
    std::sort(location_degrees.rbegin(), location_degrees.rend());

    std::vector<int> p(n); // p[facility_idx] = location_idx
    for (int i = 0; i < n; ++i) {
        p[facility_degrees[i].second] = location_degrees[i].second;
    }

    // --- Local Search (Randomized Hill Climbing) ---
    auto start_time = std::chrono::steady_clock::now();
    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    std::uniform_int_distribution<int> dist(0, n - 1);

    // Set time limit for local search based on problem size
    double max_n_val = 2000.0;
    int time_limit_ms = 100 + static_cast<int>(1850.0 * (n / max_n_val));


    while (true) {
        auto current_time = std::chrono::steady_clock::now();
        if (std::chrono::duration_cast<std::chrono::milliseconds>(current_time - start_time).count() > time_limit_ms) {
            break;
        }

        int i = dist(rng);
        int j = dist(rng);

        if (i == j) continue;

        long long dc = calculate_delta_cost(i, j, p, n, D, F);
        
        if (dc < 0) {
            std::swap(p[i], p[j]);
        }
    }

    // Output the permutation (1-based indices)
    for (int i = 0; i < n; ++i) {
        std::cout << p[i] + 1 << (i == n - 1 ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}