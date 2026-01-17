#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <ctime>
#include <numeric>

using namespace std;

// Global variables for graph and state
int n, m;
vector<vector<int>> adj;
vector<int> current_colors;
vector<int> best_colors;
int min_conflicts = -1;

// Random number generator
mt19937 rng(1337);

// Function to calculate total conflicts for the whole graph from scratch
int calculate_total_conflicts(const vector<int>& colors) {
    int conflicts = 0;
    for (int u = 1; u <= n; ++u) {
        for (int v : adj[u]) {
            if (u < v) { // Consider each edge only once
                if (colors[u] == colors[v]) {
                    conflicts++;
                }
            }
        }
    }
    return conflicts;
}

// Local search solver
void solve(double time_limit, double start_time) {
    // 1. Random initialization
    uniform_int_distribution<int> dist(1, 3);
    for (int i = 1; i <= n; ++i) {
        current_colors[i] = dist(rng);
    }

    // Calculate initial conflicts
    int current_conflicts = calculate_total_conflicts(current_colors);

    // Update global best if this random start is good
    if (min_conflicts == -1 || current_conflicts < min_conflicts) {
        min_conflicts = current_conflicts;
        best_colors = current_colors;
    }

    // Prepare node list for iteration
    vector<int> nodes(n);
    iota(nodes.begin(), nodes.end(), 1);

    bool improved = true;
    int iter = 0;
    int max_iters = 100; // Cap iterations per restart to encourage exploration via restarts

    // 2. Hill Climbing Loop
    while (improved && iter < max_iters) {
        improved = false;
        iter++;
        
        // Shuffle node processing order to prevent cycles and biases
        shuffle(nodes.begin(), nodes.end(), rng);

        for (int u : nodes) {
            // Count neighbors' colors
            int counts[4] = {0, 0, 0, 0};
            for (int v : adj[u]) {
                counts[current_colors[v]]++;
            }

            int my_color = current_colors[u];
            int my_conflicts = counts[my_color];
            
            // Find the color that minimizes conflicts for node u
            int best_color = my_color;
            int best_local_conflicts = my_conflicts;

            for (int c = 1; c <= 3; ++c) {
                if (c == my_color) continue;
                if (counts[c] < best_local_conflicts) {
                    best_local_conflicts = counts[c];
                    best_color = c;
                }
            }

            // If a better color is found, update immediately (Greedy step)
            if (best_color != my_color) {
                current_colors[u] = best_color;
                // Update total conflicts incrementally
                current_conflicts += (best_local_conflicts - my_conflicts);
                improved = true;
            }
        }

        // Update global best solution found so far
        if (current_conflicts < min_conflicts) {
            min_conflicts = current_conflicts;
            best_colors = current_colors;
        }
        
        // Check time limit inside the loop to avoid TLE
        if (iter % 10 == 0) {
            if ((double)clock() / CLOCKS_PER_SEC - start_time > time_limit) return;
        }
    }
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;

    adj.resize(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Edge case: no edges
    if (m == 0) {
        for (int i = 1; i <= n; ++i) cout << 1 << (i == n ? "" : " ");
        cout << "\n";
        return 0;
    }

    current_colors.resize(n + 1);
    best_colors.resize(n + 1);

    // Time management setup
    double start_time = (double)clock() / CLOCKS_PER_SEC;
    // Set a safe time limit (e.g., 0.85 seconds if limit is 1.0s)
    double time_limit = 0.85;

    // Iterated Local Search with Random Restarts
    while (true) {
        solve(time_limit, start_time);
        
        // If we found a perfect coloring (0 conflicts) or ran out of time, stop
        if (min_conflicts == 0) break;
        if ((double)clock() / CLOCKS_PER_SEC - start_time > time_limit) break;
    }

    // Output result
    for (int i = 1; i <= n; ++i) {
        cout << best_colors[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}