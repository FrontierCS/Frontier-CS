#include <iostream>
#include <vector>
#include <algorithm>
#include <list>
#include <numeric>
#include <set>

// Data structures for the greedy algorithm with degree updates
std::vector<std::vector<int>> adj;
std::vector<int> current_deg;
std::vector<std::list<int>> buckets;
std::vector<std::list<int>::iterator> pos_in_bucket;
std::vector<bool> removed;
int min_deg_bucket = 0;
int N;

// Removes a vertex u and updates the degrees of its neighbors
void remove_vertex(int u) {
    // This function assumes u is not yet removed
    buckets[current_deg[u]].erase(pos_in_bucket[u]);
    removed[u] = true;

    for (int v : adj[u]) {
        if (!removed[v]) {
            // Erase from old bucket
            buckets[current_deg[v]].erase(pos_in_bucket[v]);
            
            // Decrement degree and move to new bucket
            current_deg[v]--;
            buckets[current_deg[v]].push_front(v);
            pos_in_bucket[v] = buckets[current_deg[v]].begin();
            
            // Update the minimum degree pointer if necessary
            if (current_deg[v] < min_deg_bucket) {
                min_deg_bucket = current_deg[v];
            }
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int M;
    std::cin >> N >> M;

    adj.resize(N + 1);
    current_deg.assign(N + 1, 0);
    std::set<std::pair<int, int>> edge_set;

    for (int i = 0; i < M; ++i) {
        int u, v;
        std::cin >> u >> v;
        if (u > v) std::swap(u, v);
        edge_set.insert({u, v});
    }

    for(const auto& edge : edge_set) {
        int u = edge.first;
        int v = edge.second;
        adj[u].push_back(v);
        adj[v].push_back(u);
        current_deg[u]++;
        current_deg[v]++;
    }

    buckets.resize(N);
    pos_in_bucket.resize(N + 1);
    for (int i = 1; i <= N; ++i) {
        buckets[current_deg[i]].push_front(i);
        pos_in_bucket[i] = buckets[current_deg[i]].begin();
    }

    removed.assign(N + 1, false);
    std::vector<int> independent_set;
    int remaining_vertices = N;
    
    while(remaining_vertices > 0) {
        // Find the smallest degree bucket that is not empty
        while (min_deg_bucket < N && buckets[min_deg_bucket].empty()) {
            min_deg_bucket++;
        }
        if (min_deg_bucket >= N) break;

        // Select a vertex with minimum degree
        int v = buckets[min_deg_bucket].front();

        independent_set.push_back(v);
        
        // Collect v and its neighbors to be removed
        std::vector<int> to_remove_list;
        to_remove_list.push_back(v);
        for(int neighbor : adj[v]) {
            if (!removed[neighbor]) {
                to_remove_list.push_back(neighbor);
            }
        }
        
        // Remove vertices and update degrees
        for(int u : to_remove_list) {
            if (!removed[u]) {
                remove_vertex(u);
                remaining_vertices--;
            }
        }
    }

    std::vector<int> result(N + 1, 0);
    for (int v : independent_set) {
        result[v] = 1;
    }

    for (int i = 1; i <= N; ++i) {
        std::cout << result[i] << "\n";
    }

    return 0;
}