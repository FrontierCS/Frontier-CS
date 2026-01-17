#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

void solve() {
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
    
    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());

    std::vector<int> colors(n + 1);
    std::uniform_int_distribution<int> color_dist(1, 3);
    for (int i = 1; i <= n; ++i) {
        colors[i] = color_dist(rng);
    }
    
    std::vector<int> p(n);
    std::iota(p.begin(), p.end(), 1);

    const int NUM_ROUNDS = 50;
    for (int round = 0; round < NUM_ROUNDS; ++round) {
        std::shuffle(p.begin(), p.end(), rng);
        for (int u : p) {
            int counts[4] = {0, 0, 0, 0};
            for (int v : adj[u]) {
                counts[colors[v]]++;
            }
            
            int best_color = 1;
            int min_conflicts = counts[1];
            for (int c = 2; c <= 3; ++c) {
                if (counts[c] < min_conflicts) {
                    min_conflicts = counts[c];
                    best_color = c;
                }
            }
            colors[u] = best_color;
        }
    }

    for (int i = 1; i <= n; ++i) {
        std::cout << colors[i] << (i == n ? "" : " ");
    }
    std::cout << "\n";
}

int main() {
    solve();
    return 0;
}