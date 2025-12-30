#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <chrono>
#include <random>

using namespace std;

// Global variables for graph and state
int n;
int m;
vector<vector<int>> adj;
vector<int> colors; 
vector<int> best_colors;
long long current_conflicts = 0;
long long min_conflicts = -1;

// Xorshift RNG for high performance random number generation
struct Xorshift {
    uint32_t x = 123456789;
    uint32_t y = 362436069;
    uint32_t z = 521288629;
    uint32_t w = 88675123;
    
    inline uint32_t next() {
        uint32_t t = x ^ (x << 11);
        x = y; y = z; z = w;
        return w = w ^ (w >> 19) ^ (t ^ (t >> 8));
    }
    
    inline int next_int(int max_val) { // Returns integer in [0, max_val]
        return next() % (max_val + 1);
    }
    
    inline int next_range(int min_val, int max_val) { // Returns integer in [min_val, max_val]
        return min_val + next_int(max_val - min_val);
    }
    
    inline double next_double() { // Returns double in [0, 1)
        return next() / 4294967296.0;
    }
} rng;

int main() {
    // Optimize I/O operations
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

    colors.resize(n + 1);
    
    // Randomized Greedy Initialization
    // Assign colors based on minimizing local conflicts with some noise
    vector<int> p(n);
    for(int i=0; i<n; ++i) p[i] = i+1;
    // Shuffle the order of vertices
    for(int i=n-1; i>0; i--) {
        int j = rng.next_range(0, i);
        swap(p[i], p[j]);
    }

    for (int u : p) {
        int counts[4] = {0, 0, 0, 0};
        for (int v : adj[u]) {
            if (colors[v] != 0) {
                counts[colors[v]]++;
            }
        }
        
        // Find color with minimum current neighbors
        int best_c = 1;
        if (counts[2] < counts[best_c]) best_c = 2;
        if (counts[3] < counts[best_c]) best_c = 3;
        
        // Add randomness to explore different starting states
        if (rng.next_int(99) < 10) { 
            colors[u] = rng.next_range(1, 3);
        } else {
            colors[u] = best_c;
        }
    }

    // Calculate initial number of conflicting edges
    current_conflicts = 0;
    for (int u = 1; u <= n; ++u) {
        for (int v : adj[u]) {
            if (u < v && colors[u] == colors[v]) {
                current_conflicts++;
            }
        }
    }

    best_colors = colors;
    min_conflicts = current_conflicts;

    // Simulated Annealing
    double t_start = 1.0; 
    double t_end = 0.0001;
    double temp = t_start;
    
    auto start_time = chrono::high_resolution_clock::now();
    double time_limit = 0.95; // Seconds

    long long iter = 0;
    
    while (true) {
        iter++;
        // Check time every 1024 iterations to minimize overhead
        if ((iter & 1023) == 0) {
            auto curr = chrono::high_resolution_clock::now();
            chrono::duration<double> diff = curr - start_time;
            if (diff.count() > time_limit) break;
            
            // Exponential decay schedule
            double ratio = diff.count() / time_limit;
            temp = t_start * pow(t_end / t_start, ratio);
        }

        // Pick a random vertex and a new color
        int u = rng.next_range(1, n);
        int old_c = colors[u];
        // Pick one of the other two colors
        int new_c = (old_c - 1 + rng.next_range(1, 2)) % 3 + 1;

        // Calculate change in conflicts (Delta Energy)
        int delta = 0;
        for (int v : adj[u]) {
            int c_v = colors[v];
            if (c_v == old_c) delta--; // Conflict removed
            if (c_v == new_c) delta++; // Conflict added
        }

        // Metropolis criterion
        if (delta <= 0 || rng.next_double() < exp(-delta / temp)) {
            colors[u] = new_c;
            current_conflicts += delta;
            
            if (current_conflicts < min_conflicts) {
                min_conflicts = current_conflicts;
                best_colors = colors;
            }
        }
    }

    // Final Greedy Refinement (Hill Climbing) on the best found solution
    colors = best_colors;
    bool improved = true;
    while (improved) {
        improved = false;
        // Shuffle order for the greedy pass
        for(int i=n-1; i>0; i--) {
            int j = rng.next_range(0, i);
            swap(p[i], p[j]);
        }
        
        for (int u : p) {
            int c_curr = colors[u];
            int penalties[4] = {0, 0, 0, 0};
            
            // Count neighbors' colors
            for (int v : adj[u]) {
                penalties[colors[v]]++;
            }
            
            int current_penalty = penalties[c_curr];
            int best_local_c = c_curr;
            int best_local_pen = current_penalty;
            
            // Try changing u to other colors
            for(int c=1; c<=3; ++c) {
                if (c == c_curr) continue;
                if (penalties[c] < best_local_pen) {
                    best_local_pen = penalties[c];
                    best_local_c = c;
                }
            }
            
            if (best_local_c != c_curr) {
                colors[u] = best_local_c;
                improved = true;
            }
        }
    }

    // Output results
    for (int i = 1; i <= n; ++i) {
        cout << colors[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}