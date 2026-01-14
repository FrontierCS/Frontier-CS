#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>

void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

int main() {
    fast_io();
    
    int n, m;
    std::cin >> n >> m;
    
    std::vector<std::vector<int>> adj(n + 1);
    std::vector<int> degree(n + 1, 0);
    
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        degree[u]++;
        degree[v]++;
    }
    
    std::vector<int> p(n);
    std::iota(p.begin(), p.end(), 1);
    
    std::sort(p.begin(), p.end(), [&](int u, int v) {
        return degree[u] > degree[v];
    });
    
    std::vector<int> colors(n + 1, 0);
    
    // Greedy coloring based on degree
    for (int u : p) {
        std::vector<int> neighbor_colors_count(4, 0);
        for (int v : adj[u]) {
            if (colors[v] != 0) {
                neighbor_colors_count[colors[v]]++;
            }
        }
        
        int best_color = 1;
        if (neighbor_colors_count[2] < neighbor_colors_count[best_color]) {
            best_color = 2;
        }
        if (neighbor_colors_count[3] < neighbor_colors_count[best_color]) {
            best_color = 3;
        }
        colors[u] = best_color;
    }
    
    // Local search for refinement
    int num_passes = 10;
    for (int pass = 0; pass < num_passes; ++pass) {
        bool changed = false;
        for (int u : p) { // Iterate in decreasing degree order
            std::vector<int> neighbor_colors_count(4, 0);
            for (int v : adj[u]) {
                neighbor_colors_count[colors[v]]++;
            }
            
            int current_color = colors[u];
            int current_conflicts = neighbor_colors_count[current_color];
            
            if (current_conflicts == 0) {
                continue;
            }

            int best_color = 1;
            if (neighbor_colors_count[2] < neighbor_colors_count[best_color]) {
                best_color = 2;
            }
            if (neighbor_colors_count[3] < neighbor_colors_count[best_color]) {
                best_color = 3;
            }

            if (neighbor_colors_count[best_color] < current_conflicts) {
                colors[u] = best_color;
                changed = true;
            }
        }
        if (!changed) {
            break;
        }
    }

    for (int i = 1; i <= n; ++i) {
        std::cout << colors[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;
    
    return 0;
}