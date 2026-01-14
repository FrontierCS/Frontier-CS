#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <random>
#include <chrono>

using namespace std;

// Fast I/O setup
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

// Global variables to store graph and coloring state
int n, m;
vector<vector<int>> adj;
vector<int> color;
vector<int> best_color;
int current_conflicts = 0;
int min_conflicts = 2147483647;

// Random number generator setup
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

// Helper to count conflicts for a specific node and color
// Returns the number of neighbors of u that have color c
int count_conflicts(int u, int c) {
    int cnt = 0;
    for (int v : adj[u]) {
        if (color[v] == c) {
            cnt++;
        }
    }
    return cnt;
}

// Compute total conflicts for the entire graph
int compute_total_conflicts() {
    int cnt = 0;
    for (int u = 1; u <= n; ++u) {
        for (int v : adj[u]) {
            if (u < v && color[u] == color[v]) {
                cnt++;
            }
        }
    }
    return cnt;
}

int main() {
    fast_io();

    if (!(cin >> n >> m)) return 0;

    adj.resize(n + 1);
    color.resize(n + 1);
    best_color.resize(n + 1);

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Initialize with random colors
    uniform_int_distribution<int> dist_color(1, 3);
    for (int i = 1; i <= n; ++i) {
        color[i] = dist_color(rng);
    }

    current_conflicts = compute_total_conflicts();
    min_conflicts = current_conflicts;
    best_color = color;

    // Simulated Annealing parameters
    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.90; // Seconds
    
    double t_start = 5.0; // Start temperature
    double t_end = 0.001; // End temperature
    double t = t_start;
    
    uniform_int_distribution<int> dist_node(1, n);
    uniform_real_distribution<double> dist_prob(0.0, 1.0);
    uniform_int_distribution<int> dist_binary(0, 1);

    long long iter = 0;
    
    // Main Simulated Annealing Loop
    while (true) {
        // Check time every 1024 iterations to minimize overhead
        if ((iter & 1023) == 0) {
            auto curr_time = chrono::steady_clock::now();
            chrono::duration<double> elapsed = curr_time - start_time;
            if (elapsed.count() > time_limit) break;
            
            // Update temperature
            double progress = elapsed.count() / time_limit;
            t = t_start * pow(t_end / t_start, progress);
        }
        iter++;

        // Select a random vertex
        int u = dist_node(rng);
        int c_old = color[u];
        
        // Select a random new color different from the current one
        // Colors are {1, 2, 3}. The formula cycles through the other two.
        int c_new;
        if (dist_binary(rng)) {
             c_new = (c_old % 3) + 1; 
        } else {
             c_new = ((c_old + 1) % 3) + 1; 
        }

        // Calculate change in conflicts
        int conflicts_old = 0;
        int conflicts_new = 0;
        
        for (int v : adj[u]) {
            int cv = color[v];
            if (cv == c_old) conflicts_old++;
            if (cv == c_new) conflicts_new++;
        }
        
        int delta = conflicts_new - conflicts_old;
        
        // Acceptance criteria (Metropolis-Hastings)
        bool accept = false;
        if (delta <= 0) {
            accept = true;
        } else {
            if (exp(-delta / t) > dist_prob(rng)) {
                accept = true;
            }
        }
        
        if (accept) {
            color[u] = c_new;
            current_conflicts += delta;
            // Keep track of the best solution found
            if (current_conflicts < min_conflicts) {
                min_conflicts = current_conflicts;
                best_color = color;
            }
        }
    }
    
    // Final deterministic greedy improvement phase (Hill Climbing)
    // Start from the best solution found by SA to ensure we output a local optimum
    color = best_color;
    current_conflicts = min_conflicts;
    
    while(true) {
        bool changed = false;
        
        // Check time to ensure we don't TLE
        auto curr_time = chrono::steady_clock::now();
        if ((curr_time - start_time).count() > 1.98) break;

        // Iterate over all nodes and greedily pick the best color
        for (int u = 1; u <= n; ++u) {
            int old_c = color[u];
            int best_c = old_c;
            int min_bad = count_conflicts(u, old_c);
            int current_bad = min_bad;
            
            // Try all colors
            for (int c = 1; c <= 3; ++c) {
                if (c == old_c) continue;
                int bad = count_conflicts(u, c);
                if (bad < min_bad) {
                    min_bad = bad;
                    best_c = c;
                }
            }
            
            if (best_c != old_c) {
                color[u] = best_c;
                current_conflicts += (min_bad - current_bad);
                changed = true;
            }
        }
        
        if (!changed) break;
    }
    
    // Update best_color if the greedy pass improved it
    if (current_conflicts < min_conflicts) {
        min_conflicts = current_conflicts;
        best_color = color;
    }

    // Output the result
    for (int i = 1; i <= n; ++i) {
        cout << best_color[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}