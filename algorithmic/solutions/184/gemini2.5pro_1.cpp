#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <list>
#include <set>

void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

int main() {
    fast_io();

    int N, M;
    std::cin >> N >> M;

    std::vector<std::vector<int>> adj(N + 1);
    std::vector<int> degree(N + 1, 0);
    std::set<std::pair<int, int>> edges_set;

    for (int i = 0; i < M; ++i) {
        int u, v;
        std::cin >> u >> v;
        if (u > v) std::swap(u, v);
        edges_set.insert({u, v});
    }

    for(const auto& edge : edges_set) {
        int u = edge.first;
        int v = edge.second;
        adj[u].push_back(v);
        adj[v].push_back(u);
        degree[u]++;
        degree[v]++;
    }

    std::vector<std::list<int>> buckets(N);
    std::vector<std::list<int>::iterator> pos(N + 1);

    for (int i = 1; i <= N; ++i) {
        buckets[degree[i]].push_front(i);
        pos[i] = buckets[degree[i]].begin();
    }

    std::vector<int> in_set(N + 1, 0);
    std::vector<bool> removed(N + 1, false);
    int vertices_left = N;
    int min_deg_ptr = 0;

    std::vector<int> R_vec;
    R_vec.reserve(N);
    std::vector<bool> in_R(N + 1, false);

    while (vertices_left > 0) {
        while (min_deg_ptr < N && buckets[min_deg_ptr].empty()) {
            min_deg_ptr++;
        }
        if (min_deg_ptr >= N) {
            break;
        }

        int v = buckets[min_deg_ptr].front();
        
        in_set[v] = 1;

        R_vec.clear();
        R_vec.push_back(v);
        in_R[v] = true;

        for (int neighbor : adj[v]) {
            if (!removed[neighbor] && !in_R[neighbor]) {
                R_vec.push_back(neighbor);
                in_R[neighbor] = true;
            }
        }
        
        for (int u : R_vec) {
            if (!removed[u]) {
                removed[u] = true;
                vertices_left--;
                buckets[degree[u]].erase(pos[u]);
            }
        }
        
        int next_min_deg = N;
        for (int u : R_vec) {
            for (int w : adj[u]) {
                if (!removed[w]) {
                    buckets[degree[w]].erase(pos[w]);
                    degree[w]--;
                    buckets[degree[w]].push_front(w);
                    pos[w] = buckets[degree[w]].begin();
                    next_min_deg = std::min(next_min_deg, degree[w]);
                }
            }
        }
        min_deg_ptr = std::min(min_deg_ptr, next_min_deg);

        for (int u : R_vec) {
            in_R[u] = false;
        }
    }

    for (int i = 1; i <= N; ++i) {
        std::cout << in_set[i] << "\n";
    }

    return 0;
}