#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, m;
    std::cin >> n >> m;

    std::vector<std::vector<int>> adj(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    std::vector<int> color(n + 1);
    
    unsigned seed = std::chrono::high_resolution_clock::now().time_since_epoch().count();
    std::mt19937 gen(seed);
    std::uniform_int_distribution<> distrib(0, 1);

    for (int i = 1; i <= n; ++i) {
        color[i] = distrib(gen);
    }

    std::vector<int> p(n);
    std::iota(p.begin(), p.end(), 1);

    const int max_iterations = 30;
    for (int iter = 0; iter < max_iterations; ++iter) {
        bool changed = false;
        std::shuffle(p.begin(), p.end(), gen);

        for (int u : p) {
            int same_set_neighbors = 0;
            int diff_set_neighbors = 0;
            for (int v : adj[u]) {
                if (color[v] == color[u]) {
                    same_set_neighbors++;
                } else {
                    diff_set_neighbors++;
                }
            }

            if (same_set_neighbors > diff_set_neighbors) {
                color[u] = 1 - color[u];
                changed = true;
            }
        }

        if (!changed) {
            break;
        }
    }

    for (int i = 1; i <= n; ++i) {
        std::cout << color[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}