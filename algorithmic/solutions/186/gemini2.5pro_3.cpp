#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>
#include <chrono>
#include <random>

int N, M;
std::vector<std::vector<int>> adj;
std::vector<int> degree;

// DSATUR algorithm with randomized tie-breaking
std::vector<int> solve() {
    std::vector<int> p(N);
    std::iota(p.begin(), p.end(), 1);

    static std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    std::shuffle(p.begin(), p.end(), rng);

    std::vector<int> color(N + 1, 0);
    std::vector<int> saturation_degree(N + 1, 0);
    std::vector<std::vector<char>> adjacent_colors(N + 1, std::vector<char>(N + 2, 0));

    for (int i = 0; i < N; ++i) {
        int u_to_color = -1;
        int max_sat = -1;
        int max_deg = -1;

        for (int u_candidate : p) {
            if (color[u_candidate] == 0) { // If uncolored
                if (saturation_degree[u_candidate] > max_sat) {
                    max_sat = saturation_degree[u_candidate];
                    max_deg = degree[u_candidate];
                    u_to_color = u_candidate;
                } else if (saturation_degree[u_candidate] == max_sat) {
                    if (degree[u_candidate] > max_deg) {
                        max_deg = degree[u_candidate];
                        u_to_color = u_candidate;
                    }
                }
            }
        }

        std::vector<bool> used_colors(N + 2, false);
        for (int v : adj[u_to_color]) {
            if (color[v] != 0) {
                used_colors[color[v]] = true;
            }
        }

        int c = 1;
        while (used_colors[c]) {
            c++;
        }
        color[u_to_color] = c;

        for (int v : adj[u_to_color]) {
            if (color[v] == 0) { // For each uncolored neighbor
                if (!adjacent_colors[v][c]) {
                    adjacent_colors[v][c] = 1;
                    saturation_degree[v]++;
                }
            }
        }
    }
    return color;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> N >> M;

    std::vector<std::set<int>> adj_set(N + 1);
    for (int i = 0; i < M; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj_set[u].insert(v);
        adj_set[v].insert(u);
    }
    
    adj.resize(N + 1);
    degree.resize(N + 1);
    for (int i = 1; i <= N; ++i) {
        for (int neighbor : adj_set[i]) {
            adj[i].push_back(neighbor);
        }
        degree[i] = adj[i].size();
    }

    // Run once to get an initial solution
    std::vector<int> best_coloring = solve();
    int min_colors = 0;
    for(int i = 1; i <= N; ++i) {
        min_colors = std::max(min_colors, best_coloring[i]);
    }
    
    auto start_time = std::chrono::high_resolution_clock::now();
    
    // Keep trying for better solutions until time limit is almost reached
    while (std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::high_resolution_clock::now() - start_time).count() < 1900) {
        std::vector<int> current_coloring = solve();
        int current_max_color = 0;
        for (int i = 1; i <= N; ++i) {
            current_max_color = std::max(current_max_color, current_coloring[i]);
        }
        
        if (current_max_color < min_colors) {
            min_colors = current_max_color;
            best_coloring = current_coloring;
        }
    }
    
    for (int i = 1; i <= N; ++i) {
        std::cout << best_coloring[i] << "\n";
    }

    return 0;
}