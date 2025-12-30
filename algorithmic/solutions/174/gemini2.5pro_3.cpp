#include <iostream>
#include <vector>
#include <numeric>
#include <random>
#include <chrono>
#include <cmath>
#include <algorithm>
#include <utility>

// Global RNG for performance. Seeding once in main.
std::mt19937 rng;

void solve() {
    int n;
    int m;
    std::cin >> n >> m;

    std::vector<std::vector<int>> adj(n);
    std::vector<std::pair<int, int>> edges;
    if (m > 0) {
        edges.reserve(m);
    }
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.push_back({u, v});
    }

    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            std::cout << 1 << (i == n - 1 ? "" : " ");
        }
        std::cout << std::endl;
        return;
    }

    std::uniform_int_distribution<int> color_dist(1, 3);
    std::uniform_int_distribution<int> node_dist(0, n - 1);
    std::uniform_int_distribution<int> coin_flip(0, 1);
    std::uniform_real_distribution<double> prob_dist(0.0, 1.0);

    std::vector<int> colors(n);
    for (int i = 0; i < n; ++i) {
        colors[i] = color_dist(rng);
    }

    long long current_conflicts = 0;
    for (const auto& edge : edges) {
        if (colors[edge.first] == colors[edge.second]) {
            current_conflicts++;
        }
    }

    std::vector<int> best_colors = colors;
    long long best_conflicts = current_conflicts;

    const double T_INITIAL = 10.0;
    const double T_FINAL = 1e-4;
    const double TIME_LIMIT = 1.95; // Safety margin for a 2-second limit

    const double LAMBDA = -log(T_FINAL / T_INITIAL) / TIME_LIMIT;

    auto start_time = std::chrono::steady_clock::now();
    
    while (true) {
        auto current_time = std::chrono::steady_clock::now();
        double elapsed_time = std::chrono::duration<double>(current_time - start_time).count();
        if (elapsed_time > TIME_LIMIT) {
            break;
        }

        double T = T_INITIAL * exp(-LAMBDA * elapsed_time);
        
        int u = node_dist(rng);
        int old_color = colors[u];
        int new_color = (old_color - 1 + 1 + coin_flip(rng)) % 3 + 1;

        int count_old = 0;
        int count_new = 0;
        for (int v : adj[u]) {
            if (colors[v] == old_color) count_old++;
            if (colors[v] == new_color) count_new++;
        }
        int delta_E = count_new - count_old;

        if (delta_E < 0 || prob_dist(rng) < exp(-delta_E / T)) {
            colors[u] = new_color;
            current_conflicts += delta_E;
            if (current_conflicts < best_conflicts) {
                best_conflicts = current_conflicts;
                best_colors = colors;
                if (best_conflicts == 0) {
                    break;
                }
            }
        }
    }

    for (int i = 0; i < n; ++i) {
        std::cout << best_colors[i] << (i == n - 1 ? "" : " ");
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    rng.seed(std::chrono::steady_clock::now().time_since_epoch().count());
    solve();
    return 0;
}