#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Global variables to store graph and best solution found
int n, m;
vector<vector<int>> adj;
vector<int> best_c;
int min_conflicts;

// Random number generator seeded with time
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

// Function to calculate the number of conflicting edges for a given coloring
int count_conflicts(const vector<int>& c) {
    int cnt = 0;
    for (int u = 1; u <= n; ++u) {
        for (int v : adj[u]) {
            // Check each edge exactly once (u < v)
            if (u < v && c[u] == c[v]) {
                cnt++;
            }
        }
    }
    return cnt;
}

void solve() {
    // Track execution time to maximize utilization within limits
    auto start_time = chrono::steady_clock::now();
    // Set a safe time limit (e.g., 0.9s for a 1s limit)
    double time_limit = 0.90; 

    // Initialize best solution with a default valid coloring (all 1s)
    best_c.assign(n + 1, 1);
    // In worst case, all edges conflict
    min_conflicts = m; 

    // Handle case with no edges immediately
    if (m == 0) min_conflicts = 0;

    // Working variables
    vector<int> current_c(n + 1);
    vector<int> nodes(n);
    iota(nodes.begin(), nodes.end(), 1); // Fill with 1, 2, ..., n

    // Hill climbing with random restarts
    while (min_conflicts > 0) {
        // Check if we have time for another restart
        auto now = chrono::steady_clock::now();
        chrono::duration<double> elapsed = now - start_time;
        if (elapsed.count() > time_limit) break;

        // Random Initialization
        for (int i = 1; i <= n; ++i) {
            current_c[i] = uniform_int_distribution<int>(1, 3)(rng);
        }

        // Local Search (Iterative Improvement)
        bool improved = true;
        int iter = 0;
        // Limit iterations per restart to avoid spending too much time in one local optimum
        while (improved && iter < 60) {
            improved = false;
            // Randomize update order to add stochasticity
            shuffle(nodes.begin(), nodes.end(), rng);
            
            for (int u : nodes) {
                // Count neighbors of each color
                int color_counts[4] = {0, 0, 0, 0};
                for (int v : adj[u]) {
                    color_counts[current_c[v]]++;
                }

                int my_color = current_c[u];
                int current_conflicts_u = color_counts[my_color];
                
                int best_color = my_color;
                int best_conflicts_u = current_conflicts_u;

                // Try to find a color that minimizes conflicts for vertex u
                for (int c = 1; c <= 3; ++c) {
                    if (c == my_color) continue;
                    if (color_counts[c] < best_conflicts_u) {
                        best_conflicts_u = color_counts[c];
                        best_color = c;
                    }
                }

                // If improvement found, update color
                if (best_color != my_color) {
                    current_c[u] = best_color;
                    improved = true;
                }
            }
            iter++;
        }

        // Calculate score of the local optimum
        int current_total_conflicts = count_conflicts(current_c);
        
        // Update global best if improved
        if (current_total_conflicts < min_conflicts) {
            min_conflicts = current_total_conflicts;
            best_c = current_c;
        }
    }

    // Output result
    for (int i = 1; i <= n; ++i) {
        cout << best_c[i] << (i == n ? "" : " ");
    }
    cout << "\n";
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (cin >> n >> m) {
        adj.resize(n + 1);
        for (int i = 0; i < m; ++i) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
        solve();
    }
    return 0;
}