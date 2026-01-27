#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

const int MAXN = 501;
bool adj_G[MAXN][MAXN];
int N, M;

std::mt19937 rng;

// Global structures to avoid re-allocation in the loop and for performance
int colors_g[MAXN];
bool is_colored_g[MAXN];
int deg_uncolored_Gc_g[MAXN];
int sat_deg_g[MAXN];
bool neighbor_colors_g[MAXN][MAXN];
int deg_Gc[MAXN]; // Precomputed static degrees in G_complement

void solve_inplace() {
    // Reset state for a new run
    std::fill(colors_g + 1, colors_g + N + 1, 0);
    std::fill(is_colored_g + 1, is_colored_g + N + 1, false);
    std::fill(sat_deg_g + 1, sat_deg_g + N + 1, 0);
    for (int i = 1; i <= N; ++i) {
        std::fill(neighbor_colors_g[i] + 1, neighbor_colors_g[i] + N + 1, false);
    }
    std::copy(deg_Gc + 1, deg_Gc + N + 1, deg_uncolored_Gc_g + 1);
    
    std::vector<bool> used_colors_buffer(N + 2);
    
    for (int k = 0; k < N; ++k) {
        // Select vertex to color next based on DSATUR heuristic
        int max_sat = -1;
        int max_deg = -1;
        std::vector<int> candidates;
        
        for (int i = 1; i <= N; ++i) {
            if (!is_colored_g[i]) {
                if (sat_deg_g[i] > max_sat) {
                    max_sat = sat_deg_g[i];
                    max_deg = deg_uncolored_Gc_g[i];
                    candidates.clear();
                    candidates.push_back(i);
                } else if (sat_deg_g[i] == max_sat) {
                    if (deg_uncolored_Gc_g[i] > max_deg) {
                        max_deg = deg_uncolored_Gc_g[i];
                        candidates.clear();
                        candidates.push_back(i);
                    } else if (deg_uncolored_Gc_g[i] == max_deg) {
                        candidates.push_back(i);
                    }
                }
            }
        }
        
        std::uniform_int_distribution<int> distrib(0, candidates.size() - 1);
        int u = candidates[distrib(rng)];
        
        // Find the smallest available color (positive integer)
        std::fill(used_colors_buffer.begin(), used_colors_buffer.end(), false);
        for (int v = 1; v <= N; ++v) {
            if (u != v && !adj_G[u][v] && is_colored_g[v]) {
                used_colors_buffer[colors_g[v]] = true;
            }
        }
        
        int c = 1;
        while (used_colors_buffer[c]) {
            c++;
        }
        
        colors_g[u] = c;
        is_colored_g[u] = true;
        
        for (int v = 1; v <= N; ++v) {
            if (u != v && !adj_G[u][v]) { // v is a neighbor of u in G_complement
                if (!neighbor_colors_g[v][c]) {
                    neighbor_colors_g[v][c] = true;
                    sat_deg_g[v]++;
                }
                deg_uncolored_Gc_g[v]--;
            }
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    rng.seed(std::chrono::steady_clock::now().time_since_epoch().count());

    std::cin >> N >> M;
    for (int i = 0; i < M; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj_G[u][v] = adj_G[v][u] = true;
    }
    
    // Precompute static degrees in the complement graph
    for (int i = 1; i <= N; ++i) {
        int deg_G_i = 0;
        for (int j = 1; j <= N; ++j) {
            if (i != j && adj_G[i][j]) {
                deg_G_i++;
            }
        }
        deg_Gc[i] = (N - 1) - deg_G_i;
    }

    std::vector<int> best_colors(N + 1);
    int min_k = N + 1;

    auto start_time = std::chrono::steady_clock::now();
    
    int runs = 0;
    while (std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - start_time).count() < 1800) {
        solve_inplace();
        int current_k = 0;
        for (int i = 1; i <= N; ++i) {
            current_k = std::max(current_k, colors_g[i]);
        }
        if (current_k < min_k) {
            min_k = current_k;
            std::copy(colors_g + 1, colors_g + N + 1, best_colors.begin() + 1);
        }
        runs++;
    }
    
    if (runs == 0) { // Fallback if no full run completed within the time limit
        solve_inplace();
        std::copy(colors_g + 1, colors_g + N + 1, best_colors.begin() + 1);
    }
    
    for (int i = 1; i <= N; ++i) {
        std::cout << best_colors[i] << "\n";
    }
    
    return 0;
}