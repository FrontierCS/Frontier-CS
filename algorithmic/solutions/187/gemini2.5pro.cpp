#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Function to enable fast I/O
void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

// Global variables to store graph data and the resulting clique IDs (colors)
int N, M;
std::vector<std::vector<bool>> adjG;
std::vector<int> color;
std::vector<int> degreeG_prime;
std::vector<int> saturation_degree;
std::vector<std::vector<bool>> neighbor_colors_used;

// Reads the graph from standard input
void read_input() {
    std::cin >> N >> M;
    adjG.assign(N + 1, std::vector<bool>(N + 1, false));
    for (int i = 0; i < M; ++i) {
        int u, v;
        std::cin >> u >> v;
        adjG[u][v] = adjG[v][u] = true;
    }
}

// Solves the clique cover problem using the DSATUR heuristic on the complement graph
void solve() {
    // 1. Compute degrees in the complement graph G'
    degreeG_prime.assign(N + 1, 0);
    for (int i = 1; i <= N; ++i) {
        for (int j = i + 1; j <= N; ++j) {
            if (!adjG[i][j]) {
                degreeG_prime[i]++;
                degreeG_prime[j]++;
            }
        }
    }

    // Initialize data structures for DSATUR
    color.assign(N + 1, 0); // 0 indicates an uncolored vertex
    saturation_degree.assign(N + 1, 0);
    neighbor_colors_used.assign(N + 1, std::vector<bool>(N + 2, false));
    
    // The main loop of the DSATUR algorithm, one vertex is colored in each iteration
    for (int i = 0; i < N; ++i) {
        // 2. Select the next vertex to color
        // Choose the uncolored vertex with the maximum saturation degree.
        // Ties are broken by selecting the one with the maximum degree in G'.
        int best_u = -1;
        for (int v = 1; v <= N; ++v) {
            if (color[v] == 0) { // If vertex v is uncolored
                if (best_u == -1) {
                    best_u = v;
                } else {
                    if (saturation_degree[v] > saturation_degree[best_u]) {
                        best_u = v;
                    } else if (saturation_degree[v] == saturation_degree[best_u] && degreeG_prime[v] > degreeG_prime[best_u]) {
                        best_u = v;
                    }
                }
            }
        }
        int u = best_u;

        // 3. Assign the smallest possible color (clique ID)
        std::vector<bool> used_colors_by_neighbors(N + 2, false);
        // An edge in G' exists if there is no edge in G.
        for (int v = 1; v <= N; ++v) {
            if (u != v && !adjG[u][v] && color[v] != 0) {
                used_colors_by_neighbors[color[v]] = true;
            }
        }

        int c = 1;
        while (used_colors_by_neighbors[c]) {
            c++;
        }
        color[u] = c;

        // 4. Update the saturation degrees of the uncolored neighbors of u in G'
        for (int v = 1; v <= N; ++v) {
            if (u != v && !adjG[u][v] && color[v] == 0) {
                if (!neighbor_colors_used[v][c]) {
                    neighbor_colors_used[v][c] = true;
                    saturation_degree[v]++;
                }
            }
        }
    }
}

int main() {
    fast_io();
    read_input();
    solve();
    for (int i = 1; i <= N; ++i) {
        std::cout << color[i] << "\n";
    }
    return 0;
}