#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <numeric>

// A recursive function (DFS) to find edges of a spanning tree.
void find_spanning_tree_edges(int u, const std::vector<std::vector<int>>& adj, std::vector<bool>& visited, std::vector<std::pair<int, int>>& edges) {
    visited[u] = true;
    for (int v : adj[u]) {
        if (!visited[v]) {
            if (u < v) {
                edges.push_back({u, v});
            } else {
                edges.push_back({v, u});
            }
            find_spanning_tree_edges(v, adj, visited, edges);
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    // Read tree structure
    std::vector<std::vector<int>> adj_tree(n + 1);
    for (int i = 2; i <= n; ++i) {
        int p;
        std::cin >> p;
        adj_tree[p].push_back(i);
        adj_tree[i].push_back(p);
    }

    // Find leaves
    std::vector<int> leaves;
    if (n > 1) {
        for (int i = 1; i <= n; ++i) {
            if (adj_tree[i].size() == 1) {
                leaves.push_back(i);
            }
        }
    }
    std::sort(leaves.begin(), leaves.end());

    // Construct full graph including outer ring road
    std::vector<std::vector<int>> adj_full = adj_tree;
    int k = leaves.size();
    if (k > 1) {
        for (int i = 0; i < k; ++i) {
            int u = leaves[i];
            int v = leaves[(i + 1) % k];
            adj_full[u].push_back(v);
            adj_full[v].push_back(u);
        }
    }

    // Sort neighbors to get CCW order and remove duplicates
    std::vector<std::vector<int>> sorted_adj_full(n + 1);
    long long total_degree = 0;
    for (int i = 1; i <= n; ++i) {
        std::sort(adj_full[i].begin(), adj_full[i].end());
        adj_full[i].erase(std::unique(adj_full[i].begin(), adj_full[i].end()), adj_full[i].end());
        sorted_adj_full[i] = adj_full[i];
        total_degree += sorted_adj_full[i].size();
    }

    // Output K
    int K = total_degree;
    std::cout << K << "\n";

    // Assign IDs to new vertices
    std::vector<std::vector<int>> vertex_map(n + 1);
    int current_id = 1;
    for (int i = 1; i <= n; ++i) {
        vertex_map[i].resize(sorted_adj_full[i].size());
        for (size_t j = 0; j < sorted_adj_full[i].size(); ++j) {
            vertex_map[i][j] = current_id++;
        }
    }

    // Output X_i sets
    for (int i = 1; i <= n; ++i) {
        int m = sorted_adj_full[i].size();
        for (int j = 0; j < m; ++j) {
            int neighbor1 = sorted_adj_full[i][j];
            int neighbor2 = sorted_adj_full[i][(j + 1) % m];
            std::cout << 3 << " " << i << " " << neighbor1 << " " << neighbor2 << "\n";
        }
    }

    // Collect new tree edges
    std::vector<std::pair<int, int>> new_edges;
    // Intra-gadget edges (forming paths)
    for (int i = 1; i <= n; ++i) {
        int m = sorted_adj_full[i].size();
        if (m > 1) {
            for (int j = 0; j < m - 1; ++j) {
                int u1 = vertex_map[i][j];
                int u2 = vertex_map[i][j+1];
                new_edges.push_back({u1, u2});
            }
        }
    }

    // Inter-gadget edges (connecting gadgets)
    std::vector<bool> visited(n + 1, false);
    std::vector<std::pair<int, int>> st_edges;
    find_spanning_tree_edges(1, adj_full, visited, st_edges);
    
    for (const auto& edge : st_edges) {
        int u = edge.first;
        int v = edge.second;

        auto it_v_in_u = std::lower_bound(sorted_adj_full[u].begin(), sorted_adj_full[u].end(), v);
        int i = std::distance(sorted_adj_full[u].begin(), it_v_in_u);
        int m_u = sorted_adj_full[u].size();
        int id1 = vertex_map[u][(i - 1 + m_u) % m_u];

        auto it_u_in_v = std::lower_bound(sorted_adj_full[v].begin(), sorted_adj_full[v].end(), u);
        int j = std::distance(sorted_adj_full[v].begin(), it_u_in_v);
        int id2 = vertex_map[v][j];
        
        new_edges.push_back({id1, id2});
    }

    // Output new tree edges
    for (const auto& edge : new_edges) {
        std::cout << edge.first << " " << edge.second << "\n";
    }

    return 0;
}