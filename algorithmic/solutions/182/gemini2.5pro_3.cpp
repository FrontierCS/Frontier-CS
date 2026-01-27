#include <iostream>
#include <vector>
#include <algorithm>
#include <utility>
#include <list>
#include <random>
#include <chrono>

void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

int main() {
    fast_io();

    int n, m;
    std::cin >> n >> m;

    std::vector<std::pair<int, int>> all_edges;
    all_edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        if (u > v) std::swap(u, v);
        all_edges.push_back({u, v});
    }

    std::sort(all_edges.begin(), all_edges.end());
    all_edges.erase(std::unique(all_edges.begin(), all_edges.end()), all_edges.end());

    std::vector<std::vector<int>> adj(n + 1);
    std::vector<int> degree(n + 1, 0);

    for (const auto& edge : all_edges) {
        adj[edge.first].push_back(edge.second);
        adj[edge.second].push_back(edge.first);
        degree[edge.first]++;
        degree[edge.second]++;
    }

    std::vector<bool> in_cover(n + 1, false);

    // Heuristic: Greedily pick vertex with highest current degree
    // Use a bucket queue for O(1) find-max and O(1) degree updates
    std::vector<std::list<int>> buckets(n);
    std::vector<std::list<int>::iterator> pos(n + 1);
    int max_deg = 0;

    for (int i = 1; i <= n; ++i) {
        buckets[degree[i]].push_front(i);
        pos[i] = buckets[degree[i]].begin();
        if (degree[i] > max_deg) {
            max_deg = degree[i];
        }
    }

    while (max_deg > 0) {
        while (max_deg > 0 && buckets[max_deg].empty()) {
            max_deg--;
        }
        if (max_deg == 0) break;

        int u = buckets[max_deg].front();
        buckets[max_deg].pop_front();
        
        in_cover[u] = true;
        
        for (int v : adj[u]) {
            if (!in_cover[v]) {
                int old_deg_v = degree[v];
                buckets[old_deg_v].erase(pos[v]);
                
                degree[v]--;
                int new_deg_v = degree[v];
                
                buckets[new_deg_v].push_front(v);
                pos[v] = buckets[new_deg_v].begin();
            }
        }
    }

    // Refinement phase: try to remove redundant vertices from the cover
    std::vector<int> s_nodes;
    s_nodes.reserve(n);
    for(int i = 1; i <= n; ++i) {
        if (in_cover[i]) {
            s_nodes.push_back(i);
        }
    }
    
    // Process in random order to break symmetries
    unsigned seed = std::chrono::high_resolution_clock::now().time_since_epoch().count();
    std::mt19937 g(seed);
    std::shuffle(s_nodes.begin(), s_nodes.end(), g);

    for (int v : s_nodes) {
        bool removable = true;
        for (int u : adj[v]) {
            if (!in_cover[u]) {
                removable = false;
                break;
            }
        }
        if (removable) {
            in_cover[v] = false;
        }
    }

    for (int i = 1; i <= n; ++i) {
        std::cout << in_cover[i] << "\n";
    }

    return 0;
}