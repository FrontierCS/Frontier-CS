#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <random>
#include <chrono>

const int MAXN = 1001;

int n, m;
std::vector<int> adj[MAXN];
int color[MAXN];

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n >> m;
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    std::vector<std::pair<int, int>> vertices_by_degree;
    for (int i = 1; i <= n; ++i) {
        vertices_by_degree.push_back({-(int)adj[i].size(), i});
    }
    std::sort(vertices_by_degree.begin(), vertices_by_degree.end());

    // Step 1: Greedy initialization (high degree first)
    for (const auto& pair : vertices_by_degree) {
        int i = pair.second;
        int conflict_counts[4] = {0};
        for (int neighbor : adj[i]) {
            if (color[neighbor] != 0) {
                conflict_counts[color[neighbor]]++;
            }
        }
        
        int min_conflicts = n + 1;
        int best_color = 1;
        for (int c = 1; c <= 3; ++c) {
            if (conflict_counts[c] < min_conflicts) {
                min_conflicts = conflict_counts[c];
                best_color = c;
            }
        }
        color[i] = best_color;
    }
    
    // Step 2: Local search
    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    std::vector<int> p_order(n);
    std::iota(p_order.begin(), p_order.end(), 1);

    for (int iter = 0; iter < 200; ++iter) {
        bool changed = false;
        std::shuffle(p_order.begin(), p_order.end(), rng);

        for (int i : p_order) {
            int conflict_counts[4] = {0};
            for (int neighbor : adj[i]) {
                conflict_counts[color[neighbor]]++;
            }
            
            std::vector<int> best_colors;
            int min_conflicts = n + 1;

            for (int c = 1; c <= 3; ++c) {
                if (conflict_counts[c] < min_conflicts) {
                    min_conflicts = conflict_counts[c];
                    best_colors.clear();
                    best_colors.push_back(c);
                } else if (conflict_counts[c] == min_conflicts) {
                    best_colors.push_back(c);
                }
            }
            
            int new_color = best_colors[std::uniform_int_distribution<int>(0, best_colors.size() - 1)(rng)];
            if (color[i] != new_color) {
                color[i] = new_color;
                changed = true;
            }
        }

        if (!changed) {
            break;
        }
    }
    
    // Output
    for (int i = 1; i <= n; ++i) {
        std::cout << color[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}