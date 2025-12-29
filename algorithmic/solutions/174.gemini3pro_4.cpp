#include <iostream>
#include <vector>
#include <algorithm>
#include <ctime>
#include <numeric>

using namespace std;

// Fast random number generator (Xorshift128)
struct Xorshift {
    unsigned int x = 123456789, y = 362436069, z = 521288629, w = 88675123;
    inline unsigned int next() {
        unsigned int t = x ^ (x << 11);
        x = y; y = z; z = w;
        return w = w ^ (w >> 19) ^ (t ^ (t >> 8));
    }
    // Returns random integer in [0, n-1]
    inline int next(int n) { return next() % n; }
} rng;

int main() {
    // Optimize I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    long long m;
    if (!(cin >> n >> m)) return 0;

    // Adjacency list
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Best solution found so far
    vector<int> best_color(n + 1, 1);
    long long min_conflicts = -1;

    // Time management
    clock_t start_time = clock();
    double time_limit = 0.95; // Run for up to 0.95 seconds
    
    // Order of vertices for local search
    vector<int> p(n);
    iota(p.begin(), p.end(), 1);

    // Iterated Local Search
    // We restart with random configurations repeatedly until time runs out.
    while (true) {
        // Check time limit
        double elapsed = (double)(clock() - start_time) / CLOCKS_PER_SEC;
        if (elapsed > time_limit) break;

        // Random initialization
        vector<int> color(n + 1);
        for (int i = 1; i <= n; ++i) {
            color[i] = rng.next(3) + 1;
        }

        // Greedy Local Search
        bool improved = true;
        int iter = 0;
        // Limit iterations per restart to avoid spending too much time on one local optimum
        while (improved && iter < 60) {
            improved = false;
            iter++;
            
            // Shuffle vertex processing order for variety in greedy choices
            for (int i = n - 1; i > 0; i--) {
                int j = rng.next(i + 1);
                swap(p[i], p[j]);
            }

            for (int u : p) {
                int cur_c = color[u];
                // Count conflicting neighbors for each potential color
                int conflicts[4] = {0, 0, 0, 0};
                for (int v : adj[u]) {
                    conflicts[color[v]]++;
                }

                int best_c = cur_c;
                int min_c = conflicts[cur_c];

                // Check if other colors give fewer conflicts
                for (int c = 1; c <= 3; ++c) {
                    if (c == cur_c) continue;
                    if (conflicts[c] < min_c) {
                        min_c = conflicts[c];
                        best_c = c;
                    }
                }

                if (best_c != cur_c) {
                    color[u] = best_c;
                    improved = true;
                }
            }
        }

        // Calculate total conflicts for current solution
        long long current_conflicts = 0;
        for (int u = 1; u <= n; ++u) {
            for (int v : adj[u]) {
                if (u < v && color[u] == color[v]) {
                    current_conflicts++;
                }
            }
        }

        // Update global best
        if (min_conflicts == -1 || current_conflicts < min_conflicts) {
            min_conflicts = current_conflicts;
            best_color = color;
            if (min_conflicts == 0) break; // Optimal found
        }
    }

    // Output results
    for (int i = 1; i <= n; ++i) {
        cout << best_color[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}