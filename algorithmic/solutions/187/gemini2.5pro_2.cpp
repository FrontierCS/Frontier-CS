#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <chrono>
#include <random>

// Global state for best solution
int min_K;
std::vector<int> best_colors;

// Graph properties, read once
int N, M;
std::vector<std::vector<bool>> adj;
std::vector<std::vector<int>> adj_comp;
std::vector<int> degree_comp;

// Random number generator
std::mt19937 rng;

void run_dsatur() {
    std::vector<int> colors(N + 1, 0);
    std::vector<int> saturation_degree(N + 1, 0);
    std::vector<std::vector<bool>> neighbor_colors(N + 1, std::vector<bool>(N + 2, false));

    for (int i = 0; i < N; ++i) {
        // Select vertex to color
        int u_to_color = -1;
        int max_sat = -1;
        int max_deg = -1;
        std::vector<int> candidates;

        for (int u = 1; u <= N; ++u) {
            if (colors[u] != 0) continue;

            if (saturation_degree[u] > max_sat) {
                max_sat = saturation_degree[u];
                max_deg = degree_comp[u];
                candidates.clear();
                candidates.push_back(u);
            } else if (saturation_degree[u] == max_sat) {
                if (degree_comp[u] > max_deg) {
                    max_deg = degree_comp[u];
                    candidates.clear();
                    candidates.push_back(u);
                } else if (degree_comp[u] == max_deg) {
                    candidates.push_back(u);
                }
            }
        }
        
        u_to_color = candidates[rng() % candidates.size()];

        // Assign smallest possible color
        std::vector<bool> used_colors(N + 2, false);
        for (int v : adj_comp[u_to_color]) {
            if (colors[v] != 0) {
                used_colors[colors[v]] = true;
            }
        }

        int c = 1;
        while (used_colors[c]) {
            c++;
        }
        colors[u_to_color] = c;

        // Update saturation degrees of neighbors
        for (int v : adj_comp[u_to_color]) {
            if (colors[v] == 0) {
                if (!neighbor_colors[v][c]) {
                    neighbor_colors[v][c] = true;
                    saturation_degree[v]++;
                }
            }
        }
    }
    
    int current_K = 0;
    for(int i = 1; i <= N; ++i) {
        current_K = std::max(current_K, colors[i]);
    }
    
    if (min_K == -1 || current_K < min_K) {
        min_K = current_K;
        best_colors = colors;
    }
}

void solve() {
    std::cin >> N >> M;
    adj.assign(N + 1, std::vector<bool>(N + 1, false));
    for (int i = 0; i < M; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u][v] = adj[v][u] = true;
    }

    adj_comp.assign(N + 1, std::vector<int>());
    degree_comp.assign(N + 1, 0);
    for (int i = 1; i <= N; ++i) {
        for (int j = i + 1; j <= N; ++j) {
            if (!adj[i][j]) {
                adj_comp[i].push_back(j);
                adj_comp[j].push_back(i);
            }
        }
    }
    for(int i=1; i<=N; ++i) {
        degree_comp[i] = adj_comp[i].size();
    }
    
    auto start_time = std::chrono::high_resolution_clock::now();
    rng.seed(start_time.time_since_epoch().count());
    
    min_K = -1;
    
    while(true) {
        auto current_time = std::chrono::high_resolution_clock::now();
        if (std::chrono::duration_cast<std::chrono::milliseconds>(current_time - start_time).count() > 1950) {
            break;
        }
        run_dsatur();
    }
    
    for (int i = 1; i <= N; ++i) {
        std::cout << best_colors[i] << "\n";
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}