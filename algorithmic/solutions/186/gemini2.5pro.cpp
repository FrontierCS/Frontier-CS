#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <chrono>
#include <random>
#include <set>

// Global variables for convenience
int N, M;
std::vector<std::vector<int>> adj;
std::vector<int> degree;
std::mt19937 rng;

// Calculates the saturation degree of a vertex `v`.
// Saturation degree is the number of distinct colors used by its neighbors.
int calculate_saturation(int v, const std::vector<int>& colors, int max_color) {
    if (adj[v].empty()) {
        return 0;
    }
    // Using a vector as a boolean set for performance.
    // The maximum color value can't exceed N. Size N+1 is safe.
    std::vector<bool> seen_colors(max_color + 1, false);
    int count = 0;
    for (int neighbor : adj[v]) {
        if (colors[neighbor] != 0) {
            if (!seen_colors[colors[neighbor]]) {
                seen_colors[colors[neighbor]] = true;
                count++;
            }
        }
    }
    return count;
}

// Finds the smallest positive integer color not used by neighbors of `v`.
// This is also known as the First-Fit (FF) coloring rule.
int find_smallest_color(int v, const std::vector<int>& colors, int max_color) {
    if (adj[v].empty()) {
        return 1;
    }
    // Max neighbor color can be `max_color`. A new color could be `max_color + 1`.
    // Size `max_color + 2` is safe.
    std::vector<bool> used_colors(max_color + 2, false);
    for (int neighbor : adj[v]) {
        if (colors[neighbor] != 0) {
            used_colors[colors[neighbor]] = true;
        }
    }
    int c = 1;
    while (used_colors[c]) {
        c++;
    }
    return c;
}

// A single run of the DSatur heuristic with randomized tie-breaking.
std::vector<int> dsatur_run() {
    std::vector<int> colors(N + 1, 0);
    std::vector<bool> is_colored(N + 1, false);
    int max_color_so_far = 0;

    for (int i = 0; i < N; ++i) { // Color N vertices one by one
        int best_u = -1;
        int max_sat = -1;
        
        std::vector<int> sat_candidates;
        // Find all uncolored vertices with the highest saturation degree.
        for (int v = 1; v <= N; ++v) {
            if (!is_colored[v]) {
                int current_sat = calculate_saturation(v, colors, max_color_so_far);
                if (current_sat > max_sat) {
                    max_sat = current_sat;
                    sat_candidates.clear();
                    sat_candidates.push_back(v);
                } else if (current_sat == max_sat) {
                    sat_candidates.push_back(v);
                }
            }
        }

        // If there's a tie in saturation, break it using vertex degree.
        if (sat_candidates.size() == 1) {
            best_u = sat_candidates[0];
        } else {
            int max_deg_tiebreak = -1;
            std::vector<int> deg_candidates;
            for (int v : sat_candidates) {
                if (degree[v] > max_deg_tiebreak) {
                    max_deg_tiebreak = degree[v];
                    deg_candidates.clear();
                    deg_candidates.push_back(v);
                } else if (degree[v] == max_deg_tiebreak) {
                    deg_candidates.push_back(v);
                }
            }
            // If still a tie, break it randomly.
            std::uniform_int_distribution<int> dist(0, deg_candidates.size() - 1);
            best_u = deg_candidates[dist(rng)];
        }
        
        // Color the chosen vertex with the smallest available color.
        int c = find_smallest_color(best_u, colors, max_color_so_far);
        colors[best_u] = c;
        is_colored[best_u] = true;
        max_color_so_far = std::max(max_color_so_far, c);
    }
    return colors;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    // Seed the random number generator
    rng.seed(std::chrono::steady_clock::now().time_since_epoch().count());

    std::cin >> N >> M;
    adj.resize(N + 1);
    degree.assign(N + 1, 0);
    
    // Use a set to handle multiple edges and (u,v) vs (v,u) duplicates.
    std::set<std::pair<int, int>> edge_set;
    for (int i = 0; i < M; ++i) {
        int u, v;
        std::cin >> u >> v;
        if (u > v) std::swap(u, v);
        edge_set.insert({u, v});
    }

    // Build adjacency list and degree array from the unique edges.
    for (const auto& edge : edge_set) {
        int u = edge.first;
        int v = edge.second;
        adj[u].push_back(v);
        adj[v].push_back(u);
        degree[u]++;
        degree[v]++;
    }

    auto start_time = std::chrono::high_resolution_clock::now();
    
    std::vector<int> best_coloring;
    int min_colors = N + 1;
    int runs = 0;

    // Run the heuristic multiple times until time limit is approached.
    while (true) {
        auto current_time = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsed = current_time - start_time;
        // Ensure at least one run is completed.
        if (runs > 0 && elapsed.count() > 1.9) {
            break;
        }

        std::vector<int> current_coloring = dsatur_run();
        
        int current_max_color = 0;
        for (int i = 1; i <= N; ++i) {
            current_max_color = std::max(current_max_color, current_coloring[i]);
        }

        if (current_max_color < min_colors) {
            min_colors = current_max_color;
            best_coloring = current_coloring;
        }
        runs++;
    }
    
    // Output the best coloring found.
    for (int i = 1; i <= N; ++i) {
        std::cout << best_coloring[i] << "\n";
    }

    return 0;
}