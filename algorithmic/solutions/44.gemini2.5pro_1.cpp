#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <iomanip>
#include <set>

void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(nullptr);
}

struct Point {
    long long x, y;
};

// Calculate squared Euclidean distance to avoid sqrt and use integer arithmetic longer
long double dist_sq(const Point& a, const Point& b) {
    long long dx = a.x - b.x;
    long long dy = a.y - b.y;
    return static_cast<long double>(dx) * dx + static_cast<long double>(dy) * dy;
}

// Sieve of Eratosthenes to find all primes up to n-1
std::vector<bool> sieve(int n) {
    if (n < 2) return std::vector<bool>(n, false);
    std::vector<bool> is_prime(n, true);
    is_prime[0] = is_prime[1] = false;
    for (int p = 2; p * p < n; ++p) {
        if (is_prime[p]) {
            for (int i = p * p; i < n; i += p)
                is_prime[i] = false;
        }
    }
    return is_prime;
}

int main() {
    fast_io();

    int N;
    std::cin >> N;
    std::vector<Point> cities(N);
    for (int i = 0; i < N; ++i) {
        std::cin >> cities[i].x >> cities[i].y;
    }

    auto is_prime = sieve(N);

    std::vector<int> tour;
    tour.reserve(N + 1);
    tour.push_back(0);

    std::set<int> unvisited_indices;
    for (int i = 1; i < N; ++i) {
        unvisited_indices.insert(i);
    }

    int current_city_idx = 0;
    const int WINDOW_SIZE = 40;

    for (int t = 1; t < N; ++t) {
        std::vector<int> candidates;
        
        if (unvisited_indices.size() <= WINDOW_SIZE) {
            candidates.assign(unvisited_indices.begin(), unvisited_indices.end());
        } else {
            candidates.reserve(WINDOW_SIZE);
            auto it = unvisited_indices.lower_bound(current_city_idx);

            auto fwd_it = it;
            for (int i = 0; i < WINDOW_SIZE / 2 && fwd_it != unvisited_indices.end(); ++i) {
                candidates.push_back(*fwd_it);
                ++fwd_it;
            }

            if (it != unvisited_indices.begin()) {
                auto bwd_it = std::prev(it);
                for (int i = 0; i < WINDOW_SIZE / 2; ++i) {
                    candidates.push_back(*bwd_it);
                    if (bwd_it == unvisited_indices.begin()) break;
                    --bwd_it;
                }
            }
        }
        
        int best_v = -1;
        long double min_score = -1.0L;

        bool is_critical_choice = ((t + 1) % 10 == 0);
        
        for (int v_idx : candidates) {
            long double d_sq = dist_sq(cities[current_city_idx], cities[v_idx]);
            long double score = d_sq;

            if (is_critical_choice && !is_prime[v_idx]) {
                score *= 1.21L; // (1.1)^2 penalty on squared distance
            }

            if (best_v == -1 || score < min_score) {
                min_score = score;
                best_v = v_idx;
            }
        }
        
        current_city_idx = best_v;
        tour.push_back(current_city_idx);
        unvisited_indices.erase(current_city_idx);
    }

    tour.push_back(0);

    std::cout << N + 1 << "\n";
    for (int city_id : tour) {
        std::cout << city_id << "\n";
    }

    return 0;
}