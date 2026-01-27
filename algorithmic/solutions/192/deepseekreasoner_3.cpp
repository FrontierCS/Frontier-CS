#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

int main() {
    // Optimize I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    // Use 1-based indexing for vertices
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Handle edge case with no edges
    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            cout << 0 << (i == n ? "" : " ");
        }
        cout << "\n";
        return 0;
    }

    // Random number generator
    // Using a fixed seed ensures consistent behavior, though random_device could be used
    mt19937 rng(1337);

    // Track the best partition found
    vector<int> best_s(n + 1, 0);
    int max_cut_size = -1;

    // Vector for iterating vertices in random order
    vector<int> p(n);
    iota(p.begin(), p.end(), 1);

    // Time management variables
    using clock = chrono::high_resolution_clock;
    auto start_time = clock::now();
    // Set a safe time limit (e.g., 0.85 - 0.90 seconds for a typical 1s limit)
    double time_limit_sec = 0.90;

    bool first_iteration = true;

    // Restart the local search multiple times within the time limit
    while (true) {
        // Check time limit
        if (!first_iteration) {
            auto curr_time = clock::now();
            chrono::duration<double> elapsed = curr_time - start_time;
            if (elapsed.count() > time_limit_sec) break;
        }
        first_iteration = false;

        // Initialize a random partition
        vector<int> s(n + 1);
        for (int i = 1; i <= n; ++i) {
            s[i] = rng() & 1;
        }

        // Calculate initial cut size for this partition
        int current_cut = 0;
        for (int u = 1; u <= n; ++u) {
            for (int v : adj[u]) {
                if (u < v) {
                    if (s[u] != s[v]) {
                        current_cut++;
                    }
                }
            }
        }

        // Hill Climbing / Local Search
        // Repeatedly flip vertices if it improves the cut size
        while (true) {
            bool improved = false;
            shuffle(p.begin(), p.end(), rng);

            for (int u : p) {
                // Count neighbors in same set (s[u]) vs different set (!s[u])
                int same = 0;
                int diff = 0;
                for (int v : adj[u]) {
                    if (s[u] == s[v]) same++;
                    else diff++;
                }

                // If moving vertex u to the other set increases cut edges
                // (i.e., currently has more neighbors in same set than different set)
                if (same > diff) {
                    s[u] ^= 1; // Flip the set bit
                    current_cut += (same - diff);
                    improved = true;
                }
            }
            
            // If no vertex flip improved the cut in a full pass, we reached a local optimum
            if (!improved) break;
        }

        // Update the global best result if this local optimum is better
        if (current_cut > max_cut_size) {
            max_cut_size = current_cut;
            best_s = s;
        }
    }

    // Output the best partition found
    for (int i = 1; i <= n; ++i) {
        cout << best_s[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}