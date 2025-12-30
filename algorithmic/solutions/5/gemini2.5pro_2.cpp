#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <queue>

void solve() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    int m;
    std::cin >> n >> m;

    std::vector<int> a(10);
    for (int i = 0; i < 10; ++i) {
        std::cin >> a[i];
    }

    std::vector<std::vector<int>> adj(n + 1);
    std::vector<std::vector<int>> rev_adj(n + 1);
    std::vector<int> out_degree(n + 1, 0);
    std::vector<int> in_degree(n + 1, 0);
    
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        rev_adj[v].push_back(u);
        out_degree[u]++;
        in_degree[v]++;
    }

    // Heuristic part 1: Compute a reverse topological sort order to guide greedy choices.
    // This is equivalent to Kahn's algorithm on the reversed graph, which uses out-degrees
    // of the original graph.
    std::vector<int> topo_rev_pos(n + 1, -1);
    {
        std::vector<int> current_out_degree = out_degree;
        std::queue<int> q;
        for (int i = 1; i <= n; ++i) {
            if (current_out_degree[i] == 0) {
                q.push(i);
            }
        }

        std::vector<int> topo_order;
        while (!q.empty()) {
            int u = q.front();
            q.pop();
            topo_order.push_back(u);

            for (int v : rev_adj[u]) {
                current_out_degree[v]--;
                if (current_out_degree[v] == 0) {
                    q.push(v);
                }
            }
        }
        // Assign ranks. Nodes appearing earlier in topo_order are "sinks".
        // We give them higher ranks to prioritize them in the greedy search.
        for(size_t i = 0; i < topo_order.size(); ++i) {
            topo_rev_pos[topo_order[i]] = topo_order.size() - 1 - i;
        }
    }
    
    // Heuristic part 2: Greedy search from potential starting nodes.
    // Best candidates for starting nodes are those with an in-degree of 0.
    std::vector<int> start_nodes;
    for (int i = 1; i <= n; ++i) {
        if (in_degree[i] == 0) {
            start_nodes.push_back(i);
        }
    }
    
    // Fallback if no 0-in-degree nodes exist (due to cycles).
    // Start from a node with the minimum in-degree.
    if (start_nodes.empty() && n > 0) {
        int min_in_degree = n + 1;
        int best_start = -1;
        for (int i = 1; i <= n; ++i) {
            if (in_degree[i] < min_in_degree) {
                min_in_degree = in_degree[i];
                best_start = i;
            }
        }
        if (best_start != -1) {
            start_nodes.push_back(best_start);
        }
    }
    
    std::vector<int> best_path;

    for (int start_node : start_nodes) {
        std::vector<int> current_path;
        std::vector<bool> visited(n + 1, false);
        int current_v = start_node;

        while (current_v != -1 && !visited[current_v]) {
            visited[current_v] = true;
            current_path.push_back(current_v);
            
            int next_v = -1;
            int best_pos = -1;
            
            for (int neighbor : adj[current_v]) {
                if (!visited[neighbor]) {
                    if (topo_rev_pos[neighbor] > best_pos) {
                        best_pos = topo_rev_pos[neighbor];
                        next_v = neighbor;
                    }
                }
            }
            current_v = next_v;
        }
        if (current_path.size() > best_path.size()) {
            best_path = current_path;
        }
    }

    // A final fallback if no path was constructed (e.g., if n>0 but start_nodes was empty).
    if (best_path.empty() && n > 0) {
        int start_node = 1;
        std::vector<bool> visited(n + 1, false);
        int current_v = start_node;

        while (current_v != -1 && !visited[current_v]) {
            visited[current_v] = true;
            best_path.push_back(current_v);
            
            int next_v = -1;
            int best_pos = -1;
            
            for (int neighbor : adj[current_v]) {
                if (!visited[neighbor]) {
                    if (topo_rev_pos[neighbor] > best_pos) {
                        best_pos = topo_rev_pos[neighbor];
                        next_v = neighbor;
                    }
                }
            }
            current_v = next_v;
        }
    }

    std::cout << best_path.size() << "\n";
    bool first = true;
    for (int node : best_path) {
        if (!first) {
            std::cout << " ";
        }
        std::cout << node;
        first = false;
    }
    std::cout << "\n";
}

int main() {
    solve();
    return 0;
}