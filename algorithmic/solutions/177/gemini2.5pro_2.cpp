#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

void solve() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    int m;
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

    auto start_time = std::chrono::steady_clock::now();
    
    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    std::uniform_int_distribution<int> color_dist(1, 3);

    std::vector<int> best_colors(n + 1);
    long long min_conflicts = -1;
    
    do {
        std::vector<int> current_colors(n + 1);
        for (int i = 1; i <= n; ++i) {
            current_colors[i] = color_dist(rng);
        }

        std::vector<int> p(n);
        std::iota(p.begin(), p.end(), 1);

        for (int iter = 0; iter < 80; ++iter) {
            bool changed = false;
            std::shuffle(p.begin(), p.end(), rng);

            for (int v : p) {
                int counts[4] = {0, 0, 0, 0};
                for (int u : adj[v]) {
                    counts[current_colors[u]]++;
                }

                int c_old = current_colors[v];
                
                int min_val = counts[1];
                int c_best = 1;
                if (counts[2] < min_val) {
                    min_val = counts[2];
                    c_best = 2;
                }
                if (counts[3] < min_val) {
                    c_best = 3;
                }

                if (c_old != c_best) {
                    current_colors[v] = c_best;
                    changed = true;
                }
            }
            if (!changed) {
                break;
            }
        }

        long long current_conflicts = 0;
        for (const auto& edge : edges) {
            if (current_colors[edge.first] == current_colors[edge.second]) {
                current_conflicts++;
            }
        }

        if (min_conflicts == -1 || current_conflicts < min_conflicts) {
            min_conflicts = current_conflicts;
            best_colors = current_colors;
            if (min_conflicts == 0) break;
        }

    } while (std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - start_time).count() < 1900);

    for (int i = 1; i <= n; ++i) {
        std::cout << best_colors[i] << (i == n ? "" : " ");
    }
    std::cout << "\n";
}

int main() {
    solve();
    return 0;
}