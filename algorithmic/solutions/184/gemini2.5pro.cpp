#include <iostream>
#include <vector>
#include <set>
#include <algorithm>
#include <utility>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int N, M;
    std::cin >> N >> M;

    std::vector<std::vector<int>> adj(N + 1);
    std::set<std::pair<int, int>> edge_set;
    for (int i = 0; i < M; ++i) {
        int u, v;
        std::cin >> u >> v;
        if (u > v) std::swap(u, v);
        edge_set.insert({u, v});
    }

    std::vector<int> degree(N + 1, 0);
    for (const auto& edge : edge_set) {
        int u = edge.first;
        int v = edge.second;
        adj[u].push_back(v);
        adj[v].push_back(u);
        degree[u]++;
        degree[v]++;
    }
    
    std::set<std::pair<int, int>> sorted_by_degree;
    for (int i = 1; i <= N; ++i) {
        sorted_by_degree.insert({degree[i], i});
    }

    std::vector<bool> in_set(N + 1, false);
    std::vector<bool> removed(N + 1, false);

    while (!sorted_by_degree.empty()) {
        int u = sorted_by_degree.begin()->second;

        in_set[u] = true;

        std::vector<int> nodes_to_remove;
        nodes_to_remove.push_back(u);
        for(int v : adj[u]) {
            if(!removed[v]) {
                nodes_to_remove.push_back(v);
            }
        }

        // Phase 1: Mark all these nodes as removed and take them out of the priority queue.
        for(int v : nodes_to_remove) {
            if(!removed[v]) {
                removed[v] = true;
                sorted_by_degree.erase({degree[v], v});
            }
        }
        
        // Phase 2: Update degrees of affected neighbors.
        // An affected neighbor is a node `w` that is not in `nodes_to_remove`, but is adjacent to some node `v` in `nodes_to_remove`.
        for(int v : nodes_to_remove) {
            for(int w : adj[v]) {
                if(!removed[w]) {
                    // This w has lost v as a neighbor. Update its degree.
                    sorted_by_degree.erase({degree[w], w});
                    degree[w]--;
                    sorted_by_degree.insert({degree[w], w});
                }
            }
        }
    }

    for (int i = 1; i <= N; ++i) {
        std::cout << (in_set[i] ? 1 : 0) << "\n";
    }

    return 0;
}