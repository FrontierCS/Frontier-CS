#include <iostream>
#include <vector>
#include <list>
#include <algorithm>
#include <utility>

// Fast I/O
void setup_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

int main() {
    setup_io();
    int N;
    int M;
    std::cin >> N >> M;

    std::vector<std::pair<int, int>> edge_list;
    edge_list.reserve(M);
    for (int i = 0; i < M; ++i) {
        int u, v;
        std::cin >> u >> v;
        if (u > v) std::swap(u, v);
        edge_list.push_back({u, v});
    }

    std::sort(edge_list.begin(), edge_list.end());
    edge_list.erase(std::unique(edge_list.begin(), edge_list.end()), edge_list.end());

    std::vector<std::vector<int>> adj(N + 1);
    std::vector<int> initial_degree(N + 1, 0);
    for (const auto& edge : edge_list) {
        adj[edge.first].push_back(edge.second);
        adj[edge.second].push_back(edge.first);
        initial_degree[edge.first]++;
        initial_degree[edge.second]++;
    }
    
    edge_list.clear();
    edge_list.shrink_to_fit();

    // --- Greedy algorithm ---
    std::vector<int> current_degree = initial_degree;
    std::vector<std::list<int>> buckets(N);
    std::vector<std::list<int>::iterator> pos(N + 1);
    int max_degree = 0;

    for (int i = 1; i <= N; ++i) {
        buckets[current_degree[i]].push_front(i);
        pos[i] = buckets[current_degree[i]].begin();
        if (current_degree[i] > max_degree) {
            max_degree = current_degree[i];
        }
    }

    std::vector<bool> in_cover(N + 1, false);
    
    for (int k = 0; k < N; ++k) {
        while (max_degree > 0 && buckets[max_degree].empty()) {
            max_degree--;
        }
        if (max_degree <= 0) break;

        int u = buckets[max_degree].front();
        buckets[max_degree].pop_front();
        
        in_cover[u] = true;

        for (int v : adj[u]) {
            if (!in_cover[v]) {
                buckets[current_degree[v]].erase(pos[v]);
                current_degree[v]--;
                buckets[current_degree[v]].push_front(v);
                pos[v] = buckets[current_degree[v]].begin();
            }
        }
    }

    // --- Reduction step ---
    std::vector<int> cover_nodes;
    cover_nodes.reserve(N);
    for (int i = 1; i <= N; ++i) {
        if (in_cover[i]) {
            cover_nodes.push_back(i);
        }
    }
    
    // Iterate in a deterministic order (by vertex ID)
    // for (int u : cover_nodes) { // Ascending
    for (auto it = cover_nodes.rbegin(); it != cover_nodes.rend(); ++it) { // Descending
        int u = *it;
        bool redundant = true;
        for (int v : adj[u]) {
            if (!in_cover[v]) {
                redundant = false;
                break;
            }
        }
        if (redundant) {
            in_cover[u] = false;
        }
    }

    // --- Output ---
    for (int i = 1; i <= N; ++i) {
        std::cout << (in_cover[i] ? 1 : 0) << "\n";
    }

    return 0;
}