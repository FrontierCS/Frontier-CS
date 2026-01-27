#include <iostream>
#include <vector>
#include <algorithm>
#include <chrono>
#include <random>
#include <set>

// Global variables for graph representation
int N, M;
std::vector<std::vector<int>> adj;
std::vector<int> degree;

// Mersenne Twister for random numbers
std::mt19937 rng;

// DSATUR algorithm with randomized tie-breaking
std::vector<int> dsatur_solve() {
    std::vector<int> color(N + 1, 0);
    std::vector<bool> colored(N + 1, false);
    std::vector<int> saturation_degree(N + 1, 0);
    // neighbor_colors[v][c] is true if a neighbor of v has color c.
    // Max colors can be N. So size N+1 for colors is sufficient.
    std::vector<std::vector<bool>> neighbor_colors(N + 1, std::vector<bool>(N + 1, false));

    for (int i = 0; i < N; ++i) {
        int u = -1;
        
        // Select vertex to color based on max saturation degree,
        // tie-breaking with max original degree, then randomly.
        std::vector<int> candidates;
        int max_sat = -1;

        for (int j = 1; j <= N; ++j) {
            if (!colored[j]) {
                if (saturation_degree[j] > max_sat) {
                    max_sat = saturation_degree[j];
                    candidates.clear();
                    candidates.push_back(j);
                } else if (saturation_degree[j] == max_sat) {
                    candidates.push_back(j);
                }
            }
        }

        if (candidates.size() == 1) {
            u = candidates[0];
        } else {
            std::vector<int> final_candidates;
            int max_deg = -1;
            for (int v : candidates) {
                if (degree[v] > max_deg) {
                    max_deg = degree[v];
                    final_candidates.clear();
                    final_candidates.push_back(v);
                } else if (degree[v] == max_deg) {
                    final_candidates.push_back(v);
                }
            }
            std::uniform_int_distribution<int> dist(0, final_candidates.size() - 1);
            u = final_candidates[dist(rng)];
        }

        // Color vertex u with the smallest available color
        std::vector<bool> used_colors(N + 2, false);
        for (int neighbor : adj[u]) {
            if (color[neighbor] != 0) {
                used_colors[color[neighbor]] = true;
            }
        }

        int c = 1;
        while (used_colors[c]) {
            c++;
        }
        color[u] = c;
        colored[u] = true;

        // Update saturation degrees of neighbors
        for (int neighbor : adj[u]) {
            if (!colored[neighbor]) {
                if (!neighbor_colors[neighbor][c]) {
                    neighbor_colors[neighbor][c] = true;
                    saturation_degree[neighbor]++;
                }
            }
        }
    }
    return color;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    rng.seed(std::chrono::high_resolution_clock::now().time_since_epoch().count());
    
    std::cin >> N >> M;
    adj.resize(N + 1);
    degree.assign(N + 1, 0);
    std::set<std::pair<int, int>> edges;
    for (int i = 0; i < M; ++i) {
        int u, v;
        std::cin >> u >> v;
        if (u > v) std::swap(u, v);
        edges.insert({u, v});
    }

    for (const auto& edge : edges) {
        int u = edge.first;
        int v = edge.second;
        adj[u].push_back(v);
        adj[v].push_back(u);
        degree[u]++;
        degree[v]++;
    }

    std::vector<int> best_coloring;
    int min_colors = N + 1;

    auto start_time = std::chrono::high_resolution_clock::now();

    // Run once to get a baseline solution
    best_coloring = dsatur_solve();
    min_colors = 0;
    for (int i = 1; i <= N; ++i) {
        min_colors = std::max(min_colors, best_coloring[i]);
    }
    
    // Keep trying for better solutions until time runs out
    while(true){
        auto current_time = std::chrono::high_resolution_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(current_time - start_time).count();
        if (elapsed > 1900) {
            break;
        }

        std::vector<int> current_coloring = dsatur_solve();
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