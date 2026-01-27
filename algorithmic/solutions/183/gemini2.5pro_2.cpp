#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

int N, M;
std::vector<std::vector<int>> adj;
std::vector<int> degree;
std::vector<bool> best_solution;
int max_k = 0;
std::mt19937 rng;

void find_independent_set() {
    std::vector<std::pair<int, int>> sorted_vertices;
    sorted_vertices.reserve(N);
    for (int i = 1; i <= N; ++i) {
        sorted_vertices.push_back({degree[i], i});
    }

    std::sort(sorted_vertices.begin(), sorted_vertices.end());
    
    // Shuffle vertices with the same degree to introduce randomness
    if (N > 0) {
        for (size_t i = 0; i < N; ) {
            size_t j = i;
            while (j < N && sorted_vertices[j].first == sorted_vertices[i].first) {
                j++;
            }
            if (j > i + 1) {
                std::shuffle(sorted_vertices.begin() + i, sorted_vertices.begin() + j, rng);
            }
            i = j;
        }
    }

    std::vector<bool> is_removed(N + 1, false);
    std::vector<bool> current_solution(N + 1, false);
    int current_k = 0;

    for (const auto& p : sorted_vertices) {
        int v = p.second;
        if (!is_removed[v]) {
            current_solution[v] = true;
            current_k++;
            is_removed[v] = true;
            for (int u : adj[v]) {
                is_removed[u] = true;
            }
        }
    }

    if (current_k > max_k) {
        max_k = current_k;
        best_solution = current_solution;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> N >> M;
    adj.resize(N + 1);
    degree.assign(N + 1, 0);

    std::vector<std::pair<int, int>> edges;
    if (M > 0) {
        edges.reserve(M);
    }
    for (int i = 0; i < M; ++i) {
        int u, v;
        std::cin >> u >> v;
        if (u > v) std::swap(u, v);
        edges.push_back({u, v});
    }
    
    if (!edges.empty()){
        std::sort(edges.begin(), edges.end());
        edges.erase(std::unique(edges.begin(), edges.end()), edges.end());
    }

    for(const auto& edge : edges) {
        int u = edge.first;
        int v = edge.second;
        adj[u].push_back(v);
        adj[v].push_back(u);
        degree[u]++;
        degree[v]++;
    }

    rng.seed(std::chrono::steady_clock::now().time_since_epoch().count());
    
    auto start_time = std::chrono::steady_clock::now();
    
    if(N > 0) find_independent_set(); // At least one run is necessary.

    while(true) {
        auto current_time = std::chrono::steady_clock::now();
        if (std::chrono::duration_cast<std::chrono::milliseconds>(current_time - start_time).count() > 1900) {
            break;
        }
        find_independent_set();
    }

    for (int i = 1; i <= N; ++i) {
        std::cout << best_solution[i] << "\n";
    }

    return 0;
}