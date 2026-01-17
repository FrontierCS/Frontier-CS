#include <iostream>
#include <vector>
#include <algorithm>
#include <utility>

void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

int main() {
    fast_io();

    int n, m;
    std::cin >> n >> m;

    std::vector<std::vector<int>> adj(n + 1);
    std::vector<std::pair<int, int>> degrees(n);
    for (int i = 0; i < n; ++i) {
        degrees[i] = {0, i + 1};
    }

    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        degrees[u - 1].first++;
        degrees[v - 1].first++;
    }

    std::sort(degrees.rbegin(), degrees.rend());

    std::vector<int> colors(n + 1, 0);
    
    for (const auto& p : degrees) {
        int u = p.second;

        int counts[4] = {0};
        for (int v : adj[u]) {
            if (colors[v] != 0) {
                counts[colors[v]]++;
            }
        }

        int best_color = 1;
        int min_conflicts = counts[1];
        
        for (int c = 2; c <= 3; ++c) {
            if (counts[c] < min_conflicts) {
                min_conflicts = counts[c];
                best_color = c;
            }
        }
        
        colors[u] = best_color;
    }

    for (int i = 1; i <= n; ++i) {
        std::cout << colors[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}