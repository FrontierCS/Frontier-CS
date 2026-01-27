#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

int main() {
    // Optimize I/O operations for faster execution
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    // Use 1-based indexing for convenience to match input format
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Special case for no edges: any partition is valid, score is 1.
    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            cout << 0 << (i == n ? "" : " ");
        }
        cout << "\n";
        return 0;
    }

    // Store the best partition found
    vector<int> best_s(n + 1, 0);
    long long max_cut = -1;

    // Array to help iterate vertices in random order
    vector<int> p(n);
    iota(p.begin(), p.end(), 1);

    // Random number generator
    mt19937 rng(1337);

    // Timer setup
    auto start_time = chrono::steady_clock::now();
    // Set a safe time limit (e.g., 0.95s to fit within typically 1.0s or 2.0s limits)
    double time_limit = 0.95;

    // Randomized Local Search (Hill Climbing) with Restarts
    while (true) {
        // Initialize current partition randomly
        vector<int> s(n + 1);
        for (int i = 1; i <= n; ++i) {
            s[i] = rng() & 1; // 0 or 1
        }

        // Calculate initial cut size for this partition
        long long current_cut = 0;
        for (int u = 1; u <= n; ++u) {
            for (int v : adj[u]) {
                if (u < v) { // Count each edge once
                    if (s[u] != s[v]) current_cut++;
                }
            }
        }

        // Local search: greedily flip vertices to increase cut size
        bool improved = true;
        while (improved) {
            improved = false;
            // Shuffle vertex order to avoid deterministic bias
            shuffle(p.begin(), p.end(), rng);
            
            for (int u : p) {
                // Determine the effect of flipping u
                // We want to maximize edges crossing the partition.
                // If u has more neighbors in the SAME set than in the DIFFERENT set,
                // flipping u moves those edges to the cut, increasing the size.
                int same = 0;
                int diff = 0;
                for (int v : adj[u]) {
                    if (s[u] == s[v]) same++;
                    else diff++;
                }

                if (same > diff) {
                    s[u] = 1 - s[u]; // Flip
                    current_cut += (same - diff);
                    improved = true;
                }
            }
        }

        // Update global best if this local optimum is better
        if (current_cut > max_cut) {
            max_cut = current_cut;
            best_s = s;
        }

        // Check elapsed time
        auto curr_time = chrono::steady_clock::now();
        chrono::duration<double> elapsed = curr_time - start_time;
        if (elapsed.count() > time_limit) break;
    }

    // Output the best partition configuration
    for (int i = 1; i <= n; ++i) {
        cout << best_s[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}