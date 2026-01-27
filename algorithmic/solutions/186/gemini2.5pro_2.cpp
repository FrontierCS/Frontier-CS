#include <iostream>
#include <vector>
#include <algorithm>
#include <set>
#include <utility>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int N, M;
    std::cin >> N >> M;

    std::vector<std::vector<int>> adj(N + 1);
    std::vector<int> degree(N + 1, 0);
    // Use a set to handle multiple edges efficiently
    std::set<std::pair<int, int>> edges;

    for (int i = 0; i < M; ++i) {
        int u, v;
        std::cin >> u >> v;
        if (u > v) std::swap(u, v);
        if (edges.find({u, v}) == edges.end()) {
            adj[u].push_back(v);
            adj[v].push_back(u);
            degree[u]++;
            degree[v]++;
            edges.insert({u, v});
        }
    }

    std::vector<int> color(N + 1, 0);
    std::vector<int> sat_degree(N + 1, 0);
    std::vector<std::vector<int>> neighbors_with_color(N + 1, std::vector<int>(N + 1, 0));
    std::vector<bool> is_colored(N + 1, false);

    for (int i = 0; i < N; ++i) {
        int u_to_color = -1;
        
        // Find first uncolored vertex to initialize selection
        for (int v = 1; v <= N; ++v) {
            if (!is_colored[v]) {
                u_to_color = v;
                break;
            }
        }
        
        if (u_to_color == -1) {
            break; // All vertices are colored
        }

        // Find the best vertex among uncolored ones based on DSATUR
        for (int v = u_to_color + 1; v <= N; ++v) {
            if (!is_colored[v]) {
                if (sat_degree[v] > sat_degree[u_to_color]) {
                    u_to_color = v;
                } else if (sat_degree[v] == sat_degree[u_to_color]) {
                    if (degree[v] > degree[u_to_color]) {
                        u_to_color = v;
                    }
                }
            }
        }
        
        is_colored[u_to_color] = true;

        // Assign smallest possible positive integer color
        std::vector<bool> used_colors(N + 2, false);
        for (int neighbor : adj[u_to_color]) {
            if (color[neighbor] != 0) {
                used_colors[color[neighbor]] = true;
            }
        }

        int assigned_color = 1;
        while (used_colors[assigned_color]) {
            assigned_color++;
        }
        color[u_to_color] = assigned_color;

        // Update saturation degrees of neighbors
        for (int neighbor : adj[u_to_color]) {
            if (!is_colored[neighbor]) {
                if (neighbors_with_color[neighbor][assigned_color] == 0) {
                    sat_degree[neighbor]++;
                }
                neighbors_with_color[neighbor][assigned_color]++;
            }
        }
    }

    for (int i = 1; i <= N; ++i) {
        std::cout << color[i] << "\n";
    }

    return 0;
}