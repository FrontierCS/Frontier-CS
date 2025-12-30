#include <iostream>
#include <vector>
#include <algorithm>
#include <chrono>
#include <cmath>

using namespace std;

// A simple fast Xorshift pseudo-random number generator
struct Xorshift {
    unsigned int x = 123456789;
    unsigned int next() {
        x ^= x << 13;
        x ^= x >> 17;
        x ^= x << 5;
        return x;
    }
    // Returns integer in [0, k-1]
    int next(int k) {
        return next() % k;
    }
    // Returns double in [0.0, 1.0]
    double nextDouble() {
        return (double)next() / 4294967295.0;
    }
};

const int MAXN = 1005;
vector<int> adj[MAXN];
int colors[MAXN];
int best_colors[MAXN];
int n, m;

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;

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

    Xorshift rng;
    // Initialize with a random coloring
    for (int i = 1; i <= n; ++i) colors[i] = rng.next(3) + 1;

    // Calculate initial number of conflicting edges
    long long current_conflicts = 0;
    for (int u = 1; u <= n; ++u) {
        for (int v : adj[u]) {
            if (u < v && colors[u] == colors[v]) {
                current_conflicts++;
            }
        }
    }

    long long min_conflicts = current_conflicts;
    for (int i = 1; i <= n; ++i) best_colors[i] = colors[i];

    // Simulated Annealing
    auto start_time = chrono::high_resolution_clock::now();
    // Set a safe time limit (e.g., 0.85s to fit within typically 1s or 2s)
    double time_limit = 0.85; 

    double T_start = 2.0;
    double T_end = 0.01;
    double T = T_start;

    int iter = 0;
    while (true) {
        // Check time every 4096 iterations to minimize overhead
        if ((iter & 4095) == 0) {
            auto curr = chrono::high_resolution_clock::now();
            chrono::duration<double> el = curr - start_time;
            if (el.count() > time_limit) break;
            
            // Update temperature
            double progress = el.count() / time_limit;
            T = T_start * pow(T_end / T_start, progress);
        }
        iter++;

        // Pick a random vertex
        int u = rng.next(n) + 1;
        int old_c = colors[u];
        
        // Pick a new color different from current
        int new_c = (old_c % 3) + 1; 
        if (rng.next(2) == 0) new_c = (new_c % 3) + 1;

        // Calculate change in conflicts (delta)
        // delta = conflicts_with_new_color - conflicts_with_old_color
        int conf_old = 0;
        int conf_new = 0;
        for (int v : adj[u]) {
            int c_v = colors[v];
            if (c_v == old_c) conf_old++;
            if (c_v == new_c) conf_new++;
        }

        int delta = conf_new - conf_old;
        bool accept = false;
        
        if (delta <= 0) {
            accept = true;
        } else {
            // Metropolis criterion
            if (rng.nextDouble() < exp(-delta / T)) {
                accept = true;
            }
        }

        if (accept) {
            colors[u] = new_c;
            current_conflicts += delta;
            
            // Update best solution found so far
            if (current_conflicts < min_conflicts) {
                min_conflicts = current_conflicts;
                for(int i=1; i <= n; ++i) best_colors[i] = colors[i];
                if (min_conflicts == 0) break; // Optimal found
            }
        }
    }

    // Greedy Refinement / Hill Climbing on the best solution found
    for(int i=1; i<=n; ++i) colors[i] = best_colors[i];
    current_conflicts = min_conflicts;

    while (true) {
        bool changed = false;
        vector<int> nodes(n);
        for(int i=0; i<n; ++i) nodes[i] = i+1;
        // Shuffle processing order
        for(int i=n-1; i>0; --i) swap(nodes[i], nodes[rng.next(i+1)]);

        for (int u : nodes) {
            int cur_c = colors[u];
            int cur_cost = 0;
            // Calculate conflicts with current color
            for(int v : adj[u]) if(colors[v] == cur_c) cur_cost++;
            
            int best_local_c = cur_c;
            int best_local_cost = cur_cost;

            // Try the other two colors
            for(int c=1; c<=3; ++c) {
                if(c == cur_c) continue;
                int cost = 0;
                for(int v : adj[u]) if(colors[v] == c) cost++;
                
                // Strictly better to ensure convergence
                if(cost < best_local_cost) {
                    best_local_cost = cost;
                    best_local_c = c;
                }
            }

            if(best_local_c != cur_c) {
                colors[u] = best_local_c;
                current_conflicts = current_conflicts - cur_cost + best_local_cost;
                changed = true;
            }
        }
        if (!changed) break;
    }

    // Final check to ensure we output the best coloring
    if (current_conflicts < min_conflicts) {
        for(int i=1; i<=n; ++i) best_colors[i] = colors[i];
    }

    // Output result
    for (int i = 1; i <= n; ++i) {
        cout << best_colors[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}