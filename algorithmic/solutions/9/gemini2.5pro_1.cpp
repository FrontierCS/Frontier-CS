#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <queue>

// Function to solve a single test case
void solve() {
    int n;
    std::cin >> n;

    std::vector<int> p(n + 1);
    std::vector<std::vector<int>> adj(n + 1);
    for (int i = 1; i <= n; ++i) {
        std::cin >> p[i];
    }

    std::vector<std::pair<int, int>> edge_list;
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edge_list.push_back({u, v});
    }

    // Precompute next hops for all pairs
    std::vector<std::vector<int>> next_hop(n + 1, std::vector<int>(n + 1, 0));
    for (int start_node = 1; start_node <= n; ++start_node) {
        std::queue<int> q_bfs;
        q_bfs.push(start_node);
        std::vector<int> parent(n + 1, 0);
        parent[start_node] = start_node; // Sentinel for root
        std::vector<bool> visited(n + 1, false);
        visited[start_node] = true;

        while (!q_bfs.empty()) {
            int u = q_bfs.front();
            q_bfs.pop();

            for (int v : adj[u]) {
                if (!visited[v]) {
                    visited[v] = true;
                    parent[v] = u;
                    q_bfs.push(v);
                }
            }
        }

        for (int i = 1; i <= n; ++i) {
            if (i == start_node) continue;
            int curr = i;
            while (parent[curr] != start_node) {
                curr = parent[curr];
            }
            next_hop[start_node][i] = curr;
        }
    }

    std::vector<std::vector<int>> operations;
    while (true) {
        bool sorted = true;
        for (int i = 1; i <= n; ++i) {
            if (p[i] != i) {
                sorted = false;
                break;
            }
        }
        if (sorted) break;

        std::vector<int> score2_edges, score1_edges;
        for (int i = 0; i < n - 1; ++i) {
            int u = edge_list[i].first;
            int v = edge_list[i].second;
            int val_u = p[u];
            int val_v = p[v];

            bool u_wants_v = false;
            if (val_u != u) {
                u_wants_v = (next_hop[u][val_u] == v);
            }
            
            bool v_wants_u = false;
            if (val_v != v) {
                v_wants_u = (next_hop[v][val_v] == u);
            }

            if (u_wants_v && v_wants_u) {
                score2_edges.push_back(i + 1);
            } else if (u_wants_v || v_wants_u) {
                score1_edges.push_back(i + 1);
            }
        }

        std::vector<int> current_op;
        std::vector<bool> used_vertex(n + 1, false);

        for (int edge_idx : score2_edges) {
            int u = edge_list[edge_idx - 1].first;
            int v = edge_list[edge_idx - 1].second;
            if (!used_vertex[u] && !used_vertex[v]) {
                current_op.push_back(edge_idx);
                used_vertex[u] = true;
                used_vertex[v] = true;
            }
        }
        for (int edge_idx : score1_edges) {
            int u = edge_list[edge_idx - 1].first;
            int v = edge_list[edge_idx - 1].second;
            if (!used_vertex[u] && !used_vertex[v]) {
                current_op.push_back(edge_idx);
                used_vertex[u] = true;
                used_vertex[v] = true;
            }
        }
        
        operations.push_back(current_op);

        for (int edge_idx : current_op) {
            int u = edge_list[edge_idx - 1].first;
            int v = edge_list[edge_idx - 1].second;
            std::swap(p[u], p[v]);
        }
    }

    std::cout << operations.size() << "\n";
    for (const auto& op : operations) {
        std::cout << op.size();
        for (int edge_idx : op) {
            std::cout << " " << edge_idx;
        }
        std::cout << "\n";
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int t;
    std::cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}