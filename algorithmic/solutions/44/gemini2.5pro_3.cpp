#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>

struct Point {
    long long x, y;
};

std::vector<Point> cities;
// Calculate Euclidean distance between two cities
double dist(int u, int v) {
    long long dx = cities[u].x - cities[v].x;
    long long dy = cities[u].y - cities[v].y;
    return std::sqrt(static_cast<double>(dx) * dx + static_cast<double>(dy) * dy);
}

// Sieve of Eratosthenes to find prime numbers up to n
std::vector<bool> sieve(int n) {
    std::vector<bool> is_prime(n + 1, true);
    if (n >= 0) is_prime[0] = false;
    if (n >= 1) is_prime[1] = false;
    for (int p = 2; p * p <= n; ++p) {
        if (is_prime[p]) {
            for (int i = p * p; i <= n; i += p)
                is_prime[i] = false;
        }
    }
    return is_prime;
}

// Helper to get the previous city in the tour from a path index
int get_prev_city(int path_idx, const std::vector<int>& path) {
    if (path_idx == 0) return 0;
    return path[path_idx - 1];
}

// Helper to get the next city in the tour from a path index
int get_next_city(int path_idx, int n, const std::vector<int>& path) {
    if (path_idx == n - 2) return 0;
    return path[path_idx + 1];
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;
    cities.resize(n);
    for (int i = 0; i < n; ++i) {
        std::cin >> cities[i].x >> cities[i].y;
    }

    if (n <= 1) {
        std::cout << n + 1 << "\n";
        for(int i = 0; i < n; ++i) std::cout << i << "\n";
        std::cout << 0 << "\n";
        return 0;
    }

    auto is_prime = sieve(n);

    // path represents the tour of cities {1, ..., N-1}
    std::vector<int> path(n - 1);
    std::iota(path.begin(), path.end(), 1);

    const int window_size = 60;
    const int passes = 2;

    for (int pass = 0; pass < passes; ++pass) {
        // A tour position `i` corresponds to path index `i-1`.
        // A step `t` from `P[t-1]` is penalized. Critical positions `P[9], P[19], ...`
        // corresponding to path indices 8, 18, ...
        for (int i = 8; i < n - 1; i += 10) {
            if (!is_prime[path[i]]) {
                double best_delta = 1e-9; // Only accept swaps that improve the score
                int best_j = -1;
                
                for (int j_offset = -window_size; j_offset <= window_size; ++j_offset) {
                    int j = i + j_offset;
                    if (j < 0 || j >= n - 1 || i == j) continue;
                    
                    // Candidate for swap must be a prime city at a non-critical position
                    // The step from P[j+1]=path[j] is step j+2.
                    if (is_prime[path[j]] && (j + 2) % 10 != 0) {
                        int u = path[i];
                        int v = path[j];

                        double delta_euc;
                        if (std::abs(i - j) == 1) { // Adjacent swap
                            int s = std::min(i, j);
                            int city_u = path[s], city_v = path[s+1];
                            int prev_city = get_prev_city(s, path);
                            int next_city = get_next_city(s + 1, n, path);
                            delta_euc = (dist(prev_city, city_v) + dist(city_u, next_city)) -
                                        (dist(prev_city, city_u) + dist(city_v, next_city));
                        } else { // Non-adjacent swap
                            int prev_u = get_prev_city(i, path);
                            int next_u = get_next_city(i, n, path);
                            int prev_v = get_prev_city(j, path);
                            int next_v = get_next_city(j, n, path);

                            delta_euc = (dist(prev_u, v) + dist(v, next_u)) - (dist(prev_u, u) + dist(u, next_u)) +
                                        (dist(prev_v, u) + dist(u, next_v)) - (dist(prev_v, v) + dist(v, next_v));
                        }
                        
                        // Penalty is removed from step i+2, which starts at path[i]
                        double delta_pen = -0.1 * dist(u, get_next_city(i, n, path));

                        if (delta_euc + delta_pen < best_delta) {
                            best_delta = delta_euc + delta_pen;
                            best_j = j;
                        }
                    }
                }
                if (best_j != -1) {
                    std::swap(path[i], path[best_j]);
                }
            }
        }
    }

    std::cout << n + 1 << "\n";
    std::cout << 0 << "\n";
    for (int city_id : path) {
        std::cout << city_id << "\n";
    }
    std::cout << 0 << "\n";

    return 0;
}