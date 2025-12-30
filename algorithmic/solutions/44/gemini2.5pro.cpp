#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

struct City {
    long long x, y;
    int id;
};

double dist(const City& a, const City& b) {
    long long dx = a.x - b.x;
    long long dy = a.y - b.y;
    return std::sqrt(static_cast<double>(dx) * dx + static_cast<double>(dy) * dy);
}

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

double get_mult(int step_idx, int city_id, const std::vector<bool>& is_prime) {
    if (step_idx % 10 == 0 && city_id < is_prime.size() && !is_prime[city_id]) {
        return 1.1;
    }
    return 1.0;
}

double calculate_swap_delta(int i, int j, const std::vector<int>& path, const std::vector<City>& cities, const std::vector<bool>& is_prime) {
    if (i == j) return 0;
    if (j < i) std::swap(i, j);

    int u = path[i], v = path[j];
    
    if (j == i + 1) {
        int p_im1 = path[i-1];
        int p_jp1 = path[j+1];
        double old_cost = dist(cities[p_im1], cities[u]) * get_mult(i, p_im1, is_prime) +
                          dist(cities[u], cities[v]) * get_mult(i + 1, u, is_prime) +
                          dist(cities[v], cities[p_jp1]) * get_mult(j + 1, v, is_prime);
        double new_cost = dist(cities[p_im1], cities[v]) * get_mult(i, p_im1, is_prime) +
                          dist(cities[v], cities[u]) * get_mult(i + 1, v, is_prime) +
                          dist(cities[u], cities[p_jp1]) * get_mult(j + 1, u, is_prime);
        return new_cost - old_cost;
    } else {
        int p_im1 = path[i-1], p_ip1 = path[i+1];
        int p_jm1 = path[j-1], p_jp1 = path[j+1];

        double old_cost = dist(cities[p_im1], cities[u]) * get_mult(i, p_im1, is_prime) +
                          dist(cities[u], cities[p_ip1]) * get_mult(i + 1, u, is_prime) +
                          dist(cities[p_jm1], cities[v]) * get_mult(j, p_jm1, is_prime) +
                          dist(cities[v], cities[p_jp1]) * get_mult(j + 1, v, is_prime);
        
        double new_cost = dist(cities[p_im1], cities[v]) * get_mult(i, p_im1, is_prime) +
                          dist(cities[v], cities[p_ip1]) * get_mult(i + 1, v, is_prime) +
                          dist(cities[p_jm1], cities[u]) * get_mult(j, p_jm1, is_prime) +
                          dist(cities[u], cities[p_jp1]) * get_mult(j + 1, u, is_prime);
        return new_cost - old_cost;
    }
}


int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int N;
    std::cin >> N;

    std::vector<City> cities(N);
    for (int i = 0; i < N; ++i) {
        std::cin >> cities[i].x >> cities[i].y;
        cities[i].id = i;
    }

    auto is_prime = sieve(N);

    std::vector<int> p(N - 1);
    std::iota(p.begin(), p.end(), 1);

    long long x_range = cities[N-1].x - cities[0].x;
    double strip_div = N < 1000 ? N / 100.0 : N / 400.0;
    if (strip_div < 1) strip_div = 1;
    long long strip_width = 1;
    if (x_range > 0) {
        strip_width = static_cast<long long>(x_range / strip_div);
    }
    if (strip_width == 0) strip_width = 1;
    
    std::sort(p.begin(), p.end(), [&](int i, int j) {
        long long block_i = cities[i].x / strip_width;
        long long block_j = cities[j].x / strip_width;
        if (block_i != block_j) {
            return block_i < block_j;
        }
        if (block_i % 2 == 0) {
            return cities[i].y < cities[j].y;
        }
        return cities[i].y > cities[j].y;
    });

    std::vector<int> path;
    path.reserve(N + 1);
    path.push_back(0);
    path.insert(path.end(), p.begin(), p.end());
    path.push_back(0);

    std::vector<int> pos(N);
    for (int i = 0; i < N; ++i) {
        pos[path[i]] = i;
    }

    std::vector<int> bad_indices;
    if (N >= 10) {
        for (int i = 9; i < N; i += 10) {
            if (!is_prime[path[i]]) {
                bad_indices.push_back(i);
            }
        }
    }
    
    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    std::shuffle(bad_indices.begin(), bad_indices.end(), rng);

    int search_window = 250;
    if (N < 2000) search_window = N;


    for (int i : bad_indices) {
        if (!is_prime[path[i]]) {
            int u = path[i];
            
            int best_j = -1;
            double best_delta = 1e-9;

            int start_scan = std::max(1, u - search_window);
            int end_scan = std::min(N - 1, u + search_window);

            for (int v_id = start_scan; v_id <= end_scan; ++v_id) {
                if (!is_prime[v_id]) continue;
                
                int j = pos[v_id];
                if ((j + 1) % 10 == 0 || i == j) continue;

                double current_delta = calculate_swap_delta(i, j, path, cities, is_prime);

                if (current_delta < best_delta) {
                    best_delta = current_delta;
                    best_j = j;
                }
            }
            
            if (best_j != -1) {
                int j = best_j;
                int u_val = path[i];
                int v_val = path[j];

                std::swap(path[i], path[j]);
                pos[u_val] = j;
                pos[v_val] = i;
            }
        }
    }

    std::cout << N + 1 << "\n";
    for (int city_id : path) {
        std::cout << city_id << "\n";
    }

    return 0;
}