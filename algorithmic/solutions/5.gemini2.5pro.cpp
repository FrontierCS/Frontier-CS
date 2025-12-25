#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <deque>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, m;
    std::cin >> n >> m;

    // The scoring parameters are not used by the logic, but must be read from input.
    std::vector<int> a(10);
    for (int i = 0; i < 10; ++i) {
        std::cin >> a[i];
    }

    std::vector<std::vector<int>> adj(n + 1);
    std::vector<std::vector<int>> rev_adj(n + 1);
    std::vector<int> in_degree(n + 1, 0);
    std::vector<int> out_degree(n + 1, 0);

    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        rev_adj[v].push_back(u);
        out_degree[u]++;
        in_degree[v]++;
    }

    // Heuristically find a good starting node.
    int start_node = 1;
    long long max_score = -2000000001LL; 
    for (int i = 1; i <= n; ++i) {
        long long current_score = (long long)out_degree[i] - in_degree[i];
        if (current_score > max_score) {
            max_score = current_score;
            start_node = i;
        }
    }

    std::deque<int> path;
    path.push_back(start_node);
    std::vector<bool> visited(n + 1, false);
    visited[start_node] = true;

    while (path.size() < n) {
        bool extended = false;

        // Try to extend forward from the back of the path.
        int u_fwd = path.back();
        int best_v_fwd = -1;
        int min_in = n + 1;

        for (int v : adj[u_fwd]) {
            if (!visited[v]) {
                if (best_v_fwd == -1 || in_degree[v] < min_in || (in_degree[v] == min_in && v < best_v_fwd)) {
                    min_in = in_degree[v];
                    best_v_fwd = v;
                }
            }
        }

        if (best_v_fwd != -1) {
            path.push_back(best_v_fwd);
            visited[best_v_fwd] = true;
            extended = true;
            continue;
        }

        // If forward extension fails, try to extend backward from the front of the path.
        int u_bwd = path.front();
        int best_v_bwd = -1;
        int min_out = n + 1;

        for (int v : rev_adj[u_bwd]) {
            if (!visited[v]) {
                if (best_v_bwd == -1 || out_degree[v] < min_out || (out_degree[v] == min_out && v < best_v_bwd)) {
                    min_out = out_degree[v];
                    best_v_bwd = v;
                }
            }
        }
        
        if (best_v_bwd != -1) {
            path.push_front(best_v_bwd);
            visited[best_v_bwd] = true;
            extended = true;
            continue;
        }

        // If unable to extend in either direction, break.
        if (!extended) {
            break;
        }
    }

    std::cout << path.size() << "\n";
    for (size_t i = 0; i < path.size(); ++i) {
        std::cout << path[i] << (i == path.size() - 1 ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}