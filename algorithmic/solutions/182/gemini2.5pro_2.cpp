#include <iostream>
#include <vector>
#include <algorithm>
#include <list>
#include <utility>

void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

int main() {
    fast_io();

    int n, m;
    std::cin >> n >> m;

    // Read edges and remove duplicates for a simple graph representation
    std::vector<std::pair<int, int>> edges;
    edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        if (u > v) std::swap(u, v);
        edges.push_back({u, v});
    }

    std::sort(edges.begin(), edges.end());
    edges.erase(std::unique(edges.begin(), edges.end()), edges.end());

    // Build adjacency list and compute initial degrees
    std::vector<std::vector<int>> adj(n + 1);
    std::vector<int> current_degree(n + 1, 0);

    for (const auto& edge : edges) {
        adj[edge.first].push_back(edge.second);
        adj[edge.second].push_back(edge.first);
        current_degree[edge.first]++;
        current_degree[edge.second]++;
    }

    // Bucket sort vertices by degree for efficient max-degree vertex finding
    std::vector<std::list<int>> buckets(n);
    std::vector<std::list<int>::iterator> pos(n + 1);
    int max_degree = 0;

    for (int i = 1; i <= n; ++i) {
        buckets[current_degree[i]].push_front(i);
        pos[i] = buckets[current_degree[i]].begin();
        if (current_degree[i] > max_degree) {
            max_degree = current_degree[i];
        }
    }

    std::vector<char> in_cover(n + 1, 0);
    std::vector<int> cover_nodes_ordered;
    cover_nodes_ordered.reserve(n);

    // Greedy algorithm: repeatedly pick vertex with highest degree
    for (int i = 0; i < n; ++i) {
        while (max_degree > 0 && buckets[max_degree].empty()) {
            max_degree--;
        }
        if (max_degree == 0) break;

        int u = buckets[max_degree].front();
        buckets[max_degree].pop_front();
        
        in_cover[u] = 1;
        cover_nodes_ordered.push_back(u);
        current_degree[u] = -1; // Mark as processed

        // Update degrees of neighbors
        for (int v : adj[u]) {
            if (!in_cover[v]) {
                int deg_v = current_degree[v];
                buckets[deg_v].erase(pos[v]);
                current_degree[v]--;
                buckets[current_degree[v]].push_front(v);
                pos[v] = buckets[current_degree[v]].begin();
            }
        }
    }
    
    // Reduction phase: try to remove redundant vertices from the cover
    // Iterate in reverse order of addition (nodes added last are more likely to be redundant)
    std::reverse(cover_nodes_ordered.begin(), cover_nodes_ordered.end());
    
    for (int u : cover_nodes_ordered) {
        bool is_redundant = true;
        for (int v : adj[u]) {
            if (!in_cover[v]) {
                is_redundant = false;
                break;
            }
        }
        if (is_redundant) {
            in_cover[u] = 0;
        }
    }

    for (int i = 1; i <= n; ++i) {
        std::cout << static_cast<int>(in_cover[i]) << "\n";
    }

    return 0;
}