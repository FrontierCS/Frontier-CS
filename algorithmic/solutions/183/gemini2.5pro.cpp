#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <list>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int N, M;
    std::cin >> N >> M;

    std::vector<std::vector<int>> adj(N + 1);
    for (int i = 0; i < M; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    std::vector<int> degree(N + 1);
    for (int i = 1; i <= N; ++i) {
        std::sort(adj[i].begin(), adj[i].end());
        adj[i].erase(std::unique(adj[i].begin(), adj[i].end()), adj[i].end());
        degree[i] = adj[i].size();
    }
    
    std::vector<bool> removed(N + 1, false);
    std::vector<std::list<int>> nodes_by_degree(N);
    std::vector<std::list<int>::iterator> node_iters(N + 1);
    
    for (int i = 1; i <= N; ++i) {
        node_iters[i] = nodes_by_degree[degree[i]].insert(nodes_by_degree[degree[i]].end(), i);
    }
    
    std::vector<int> ans(N + 1, 0);
    int num_processed = 0;
    int current_min_degree = 0;

    while (num_processed < N) {
        while (current_min_degree < N && nodes_by_degree[current_min_degree].empty()) {
            current_min_degree++;
        }
        if (current_min_degree == N) {
            break;
        }
        
        int v = nodes_by_degree[current_min_degree].front();
        
        ans[v] = 1;
        
        std::vector<int> to_remove_nodes;
        to_remove_nodes.push_back(v);
        for (int neighbor : adj[v]) {
            if (!removed[neighbor]) {
                to_remove_nodes.push_back(neighbor);
            }
        }
        
        for (int u : to_remove_nodes) {
            removed[u] = true;
        }
        
        for (int u : to_remove_nodes) {
            num_processed++;
            nodes_by_degree[degree[u]].erase(node_iters[u]);
            
            for (int w : adj[u]) {
                if (!removed[w]) {
                    nodes_by_degree[degree[w]].erase(node_iters[w]);
                    degree[w]--;
                    node_iters[w] = nodes_by_degree[degree[w]].insert(nodes_by_degree[degree[w]].end(), w);
                    if (degree[w] < current_min_degree) {
                         current_min_degree = degree[w];
                    }
                }
            }
        }
    }
    
    for (int i = 1; i <= N; ++i) {
        std::cout << ans[i] << "\n";
    }
    
    return 0;
}