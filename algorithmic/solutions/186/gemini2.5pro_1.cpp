#include <iostream>
#include <vector>
#include <algorithm>
#include <utility>

void solve() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, m;
    std::cin >> n >> m;

    std::vector<std::vector<int>> adj(n + 1);
    std::vector<int> degree(n + 1, 0);
    
    std::vector<std::pair<int, int>> edge_list;
    edge_list.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        if (u > v) std::swap(u, v);
        if (u != v) {
            edge_list.push_back({u, v});
        }
    }

    std::sort(edge_list.begin(), edge_list.end());
    edge_list.erase(std::unique(edge_list.begin(), edge_list.end()), edge_list.end());

    for (const auto& edge : edge_list) {
        int u = edge.first;
        int v = edge.second;
        adj[u].push_back(v);
        adj[v].push_back(u);
        degree[u]++;
        degree[v]++;
    }

    std::vector<int> color(n + 1, 0);
    std::vector<int> sat_degree(n + 1, 0);
    std::vector<std::vector<bool>> adj_colors(n + 1, std::vector<bool>(n + 2, false));
    std::vector<int> uncolored_degree = degree;

    for (int i = 0; i < n; ++i) {
        int u_to_color = -1;
        int max_sat = -1;
        int max_deg = -1;

        for (int u = 1; u <= n; ++u) {
            if (color[u] == 0) {
                if (sat_degree[u] > max_sat) {
                    max_sat = sat_degree[u];
                    max_deg = uncolored_degree[u];
                    u_to_color = u;
                } else if (sat_degree[u] == max_sat) {
                    if (uncolored_degree[u] > max_deg) {
                        max_deg = uncolored_degree[u];
                        u_to_color = u;
                    }
                }
            }
        }
        
        if (u_to_color == -1) {
            for(int u = 1; u <= n; ++u) {
                if (color[u] == 0) {
                    u_to_color = u;
                    break;
                }
            }
        }

        std::vector<bool> used_colors_by_neighbors(n + 2, false);
        for (int neighbor : adj[u_to_color]) {
            if (color[neighbor] != 0) {
                used_colors_by_neighbors[color[neighbor]] = true;
            }
        }

        int c = 1;
        while (used_colors_by_neighbors[c]) {
            c++;
        }
        color[u_to_color] = c;

        for (int neighbor : adj[u_to_color]) {
            uncolored_degree[neighbor]--;
            if (color[neighbor] == 0) {
                if (!adj_colors[neighbor][c]) {
                    adj_colors[neighbor][c] = true;
                    sat_degree[neighbor]++;
                }
            }
        }
    }

    for (int i = 1; i <= n; ++i) {
        std::cout << color[i] << "\n";
    }
}

int main() {
    solve();
    return 0;
}