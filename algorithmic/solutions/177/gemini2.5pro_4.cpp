#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

void solve() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, m;
    std::cin >> n >> m;

    std::vector<std::vector<int>> adj(n);
    if (m > 0) {
        for (int i = 0; i < m; ++i) {
            int u, v;
            std::cin >> u >> v;
            --u; --v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
    }

    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    
    std::vector<int> best_colors(n);
    long long min_conflicts = -1;

    auto start_time = std::chrono::steady_clock::now();
    
    // Multi-start local search
    while(true) {
        auto current_time = std::chrono::steady_clock::now();
        if (std::chrono::duration_cast<std::chrono::milliseconds>(current_time - start_time).count() > 1900) {
            break;
        }

        std::vector<int> current_colors(n);
        for (int i = 0; i < n; ++i) {
            current_colors[i] = rng() % 3;
        }

        if (n > 0) {
            std::vector<int> p(n);
            std::iota(p.begin(), p.end(), 0);

            // A few rounds of local search
            for (int iter = 0; iter < 80; ++iter) {
                std::shuffle(p.begin(), p.end(), rng);
                bool changed = false;

                for (int u : p) {
                    if (adj[u].empty()) continue;

                    int counts[3] = {0, 0, 0};
                    for (int v : adj[u]) {
                        counts[current_colors[v]]++;
                    }

                    int current_color = current_colors[u];
                    int current_conflicts_u = counts[current_color];

                    if (current_conflicts_u == 0) continue;

                    int min_conflicts_u = current_conflicts_u;
                    for (int c = 0; c < 3; ++c) {
                        if (counts[c] < min_conflicts_u) {
                            min_conflicts_u = counts[c];
                        }
                    }
                    
                    if (min_conflicts_u < current_conflicts_u) {
                        std::vector<int> best_options;
                        for (int c = 0; c < 3; ++c) {
                            if (counts[c] == min_conflicts_u) {
                                best_options.push_back(c);
                            }
                        }
                        current_colors[u] = best_options[rng() % best_options.size()];
                        changed = true;
                    }
                }
                if (!changed) break;
            }
        }

        long long current_total_conflicts = 0;
        if (m > 0) {
            for (int u = 0; u < n; ++u) {
                for (int v : adj[u]) {
                    if (u < v && current_colors[u] == current_colors[v]) {
                        current_total_conflicts++;
                    }
                }
            }
        }
       
        if (min_conflicts == -1 || current_total_conflicts < min_conflicts) {
            min_conflicts = current_total_conflicts;
            best_colors = current_colors;
            if (min_conflicts == 0) {
                 break;
            }
        }
    }

    for (int i = 0; i < n; ++i) {
        std::cout << best_colors[i] + 1 << (i == n - 1 ? "" : " ");
    }
    std::cout << "\n";
}

int main() {
    solve();
    return 0;
}