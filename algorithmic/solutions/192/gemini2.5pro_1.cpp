#include <iostream>
#include <vector>
#include <queue>
#include <numeric>
#include <algorithm>
#include <random>

void setup_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

int main() {
    setup_io();

    int n, m;
    std::cin >> n >> m;

    std::vector<std::vector<int>> adj(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            std::cout << "0" << (i == n - 1 ? "" : " ");
        }
        std::cout << "\n";
        return 0;
    }

    std::vector<int> partition(n + 1, -1);

    // Phase 1: Initial partition using a greedy 2-coloring approach (BFS).
    for (int i = 1; i <= n; ++i) {
        if (partition[i] == -1) {
            std::queue<int> q;
            q.push(i);
            partition[i] = 0;

            while (!q.empty()) {
                int u = q.front();
                q.pop();

                for (int v : adj[u]) {
                    if (partition[v] == -1) {
                        partition[v] = 1 - partition[u];
                        q.push(v);
                    }
                }
            }
        }
    }

    // Phase 2: Refine the partition using iterative local search.
    std::vector<int> vertices(n);
    std::iota(vertices.begin(), vertices.end(), 1);
    
    std::mt19937 rng(42);

    const int max_iterations = 30;
    for (int iter = 0; iter < max_iterations; ++iter) {
        std::shuffle(vertices.begin(), vertices.end(), rng);
        bool improved_in_pass = false;
        
        for (int u : vertices) {
            int neighbors_in_same_set = 0;
            int neighbors_in_other_set = 0;
            
            for (int v : adj[u]) {
                if (partition[v] == partition[u]) {
                    neighbors_in_same_set++;
                } else {
                    neighbors_in_other_set++;
                }
            }
            
            if (neighbors_in_same_set > neighbors_in_other_set) {
                partition[u] = 1 - partition[u];
                improved_in_pass = true;
            }
        }
        
        if (!improved_in_pass) {
            break;
        }
    }

    for (int i = 1; i <= n; ++i) {
        std::cout << partition[i] << (i == n ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}