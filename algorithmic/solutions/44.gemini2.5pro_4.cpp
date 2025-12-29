#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <tuple>

// Structure to hold city coordinates
struct Point {
    long long x, y;
};

// Global variables for city data and primality information
std::vector<Point> cities;
std::vector<bool> is_prime;
int N;

// Sieve of Eratosthenes to precompute prime numbers up to n
void sieve(int n) {
    if (n < 0) return;
    is_prime.assign(n + 1, true);
    if (n >= 0) is_prime[0] = false;
    if (n >= 1) is_prime[1] = false;
    for (int p = 2; p * p <= n; ++p) {
        if (is_prime[p]) {
            for (int i = p * p; i <= n; i += p)
                is_prime[i] = false;
        }
    }
}

// Calculate Euclidean distance between two cities
double dist(int c1, int c2) {
    long long dx = cities[c1].x - cities[c2].x;
    long long dy = cities[c1].y - cities[c2].y;
    return std::sqrt(static_cast<double>(dx) * dx + static_cast<double>(dy) * dy);
}

// Calculate the penalized cost of a single step in the tour
double cost_step(int step_idx, int from_city, int to_city) {
    double multiplier = 1.0;
    if (step_idx % 10 == 0 && !is_prime[from_city]) {
        multiplier = 1.1;
    }
    return multiplier * dist(from_city, to_city);
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    // Read input
    std::cin >> N;
    cities.resize(N);
    for (int i = 0; i < N; ++i) {
        std::cin >> cities[i].x >> cities[i].y;
    }

    // Precompute primes
    sieve(N - 1);

    // Initialize path to the baseline: 0, 1, 2, ..., N-1, 0
    std::vector<int> p(N + 1);
    std::iota(p.begin(), p.begin() + N, 0);
    p[N] = 0;

    // Hyperparameters for the local search heuristic
    int W = 400; // Search window size for swaps
    int passes = 3; // Number of improvement passes

    for (int pass = 0; pass < passes; ++pass) {
        // Identify "bad sources": non-prime cities at penalized positions
        std::vector<int> bad_sources;
        for (int i = 1; i < N; ++i) {
            // Step i+1 is from p[i] to p[i+1]. Penalized if (i+1) is a multiple of 10.
            if ((i + 1) % 10 == 0 && !is_prime[p[i]]) {
                bad_sources.push_back(i);
            }
        }
        
        if (bad_sources.empty()) break; // No more improvements possible

        // For each bad source, find the best swap partner in its local window
        std::vector<std::tuple<double, int, int>> best_swaps;
        for (int i : bad_sources) {
            double best_delta = 1e-9; // Small positive value to only consider improving swaps
            int best_j = -1;

            // Search for a prime city in a window around i
            for (int j = std::max(1, i - W); j <= std::min(N - 1, i + W); ++j) {
                if (i == j) continue;
                // Swap partner must be prime and not at another penalized position
                if (!is_prime[p[j]] || (j + 1) % 10 == 0) continue;

                double current_cost, new_cost;
                
                // Calculate cost change for swapping p[i] and p[j]
                if (std::abs(i - j) == 1) { // Adjacent swap
                    int min_idx = std::min(i, j);
                    int max_idx = std::max(i, j);
                    
                    int p_prev = p[min_idx - 1];
                    int p_curr1 = p[min_idx];
                    int p_curr2 = p[max_idx];
                    int p_next = p[max_idx + 1];

                    current_cost = cost_step(min_idx, p_prev, p_curr1) + 
                                   cost_step(max_idx, p_curr1, p_curr2) + 
                                   cost_step(max_idx + 1, p_curr2, p_next);
                    new_cost = cost_step(min_idx, p_prev, p_curr2) + 
                               cost_step(max_idx, p_curr2, p_curr1) + 
                               cost_step(max_idx + 1, p_curr1, p_next);
                } else { // Non-adjacent swap
                    int u = p[i], v = p[j];
                    int p_im1 = p[i - 1], p_ip1 = p[i + 1];
                    int p_jm1 = p[j - 1], p_jp1 = p[j + 1];

                    current_cost = cost_step(i, p_im1, u) + cost_step(i + 1, u, p_ip1) +
                                   cost_step(j, p_jm1, v) + cost_step(j + 1, v, p_jp1);
                    new_cost = cost_step(i, p_im1, v) + cost_step(i + 1, v, p_ip1) +
                               cost_step(j, p_jm1, u) + cost_step(j + 1, u, p_jp1);
                }

                double delta = new_cost - current_cost;
                if (delta < best_delta) {
                    best_delta = delta;
                    best_j = j;
                }
            }
            if (best_j != -1) {
                best_swaps.emplace_back(-best_delta, i, best_j);
            }
        }

        // Sort potential swaps by gain (descending)
        std::sort(best_swaps.rbegin(), best_swaps.rend());

        // Greedily apply the best non-conflicting swaps
        std::vector<bool> pos_swapped(N + 1, false);
        for (const auto& swap_tuple : best_swaps) {
            int i = std::get<1>(swap_tuple);
            int j = std::get<2>(swap_tuple);

            if (!pos_swapped[i] && !pos_swapped[j]) {
                std::swap(p[i], p[j]);
                pos_swapped[i] = true;
                pos_swapped[j] = true;
            }
        }
    }

    // Output the final path
    std::cout << N + 1 << "\n";
    for (int i = 0; i <= N; ++i) {
        std::cout << p[i] << "\n";
    }

    return 0;
}