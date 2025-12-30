#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, m;
    std::cin >> n >> m;

    std::vector<std::vector<int>> adj(n + 1);
    std::vector<std::pair<int, int>> edges;
    if (m > 0) {
        edges.reserve(m);
    }
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.push_back({u, v});
    }

    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            std::cout << 1 << (i == n ? "" : " ");
        }
        std::cout << "\n";
        return 0;
    }

    auto seed = std::chrono::high_resolution_clock::now().time_since_epoch().count();
    std::mt19937 rng(seed);
    std::uniform_int_distribution<int> color_dist(1, 3);

    std::vector<int> best_colors(n + 1);
    int min_total_conflicts = m + 1;

    auto start_time = std::chrono::high_resolution_clock::now();
    double time_limit_seconds = 1.95; 

    while (true) {
        auto current_time = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsed = current_time - start_time;
        if (elapsed.count() > time_limit_seconds) {
            break;
        }

        std::vector<int> current_colors(n + 1);
        for (int i = 1; i <= n; ++i) {
            current_colors[i] = color_dist(rng);
        }

        int current_total_conflicts = 0;
        for (const auto& edge : edges) {
            if (current_colors[edge.first] == current_colors[edge.second]) {
                current_total_conflicts++;
            }
        }

        const int MAX_PASSES = 80;
        for (int pass = 0; pass < MAX_PASSES; ++pass) {
            bool changed_in_pass = false;
            std::vector<int> p(n);
            std::iota(p.begin(), p.end(), 1);
            std::shuffle(p.begin(), p.end(), rng);

            for (int u : p) {
                int counts[4] = {0, 0, 0, 0};
                for (int v : adj[u]) {
                    counts[current_colors[v]]++;
                }

                int old_color = current_colors[u];
                int old_conflicts_for_u = counts[old_color];
                
                if (old_conflicts_for_u == 0) {
                    continue;
                }

                int best_color = old_color;
                int min_conflicts_for_u = old_conflicts_for_u;

                for (int c = 1; c <= 3; ++c) {
                    if (counts[c] < min_conflicts_for_u) {
                        min_conflicts_for_u = counts[c];
                        best_color = c;
                    }
                }
                
                if (best_color != old_color) {
                    current_colors[u] = best_color;
                    current_total_conflicts += (min_conflicts_for_u - old_conflicts_for_u);
                    changed_in_pass = true;
                }
            }
            if (!changed_in_pass && pass > 3) {
                break; 
            }
        }

        if (current_total_conflicts < min_total_conflicts) {
            min_total_conflicts = current_total_conflicts;
            best_colors = current_colors;
            if (min_total_conflicts == 0) {
                break;
            }
        }
    }

    for (int i = 1; i <= n; ++i) {
        std::cout << best_colors[i] << (i == n ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}