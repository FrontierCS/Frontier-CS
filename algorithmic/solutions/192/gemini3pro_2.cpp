#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <ctime>

using namespace std;

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    // Graph storage using adjacency list
    vector<vector<int>> adj(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v; // Convert 1-based indexing to 0-based
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Random number generator
    mt19937 rng((unsigned int)time(NULL));

    // Best solution tracking
    vector<int> best_partition(n, 0); // Stores the best assignment found (0 or 1)
    long long best_cut = -1;

    // Working variables
    vector<int> p(n);
    iota(p.begin(), p.end(), 0); // Permutation vector 0..n-1
    vector<int> current_partition(n);

    // Time management
    clock_t start_time = clock();
    // Set a safe time limit slightly less than typical 1.0s or 2.0s limits
    double time_limit = 0.95; 

    bool first_iter = true;

    // Iterated Local Search (Random Restarts + Hill Climbing)
    while (true) {
        // Check time limit
        if (!first_iter) {
            double elapsed = (double)(clock() - start_time) / CLOCKS_PER_SEC;
            if (elapsed > time_limit) break;
        }
        first_iter = false;

        // Initialize with a random partition
        for (int i = 0; i < n; ++i) {
            current_partition[i] = rng() % 2;
        }

        // Calculate initial cut size for the random partition
        long long current_cut = 0;
        for (int u = 0; u < n; ++u) {
            for (int v : adj[u]) {
                if (u < v) { // Avoid double counting edges
                    if (current_partition[u] != current_partition[v]) {
                        current_cut++;
                    }
                }
            }
        }

        // Hill Climbing Phase
        while (true) {
            bool improved = false;
            // Shuffle vertex processing order to add randomness and avoid cycles
            shuffle(p.begin(), p.end(), rng);

            for (int u : p) {
                // Calculate gain of flipping vertex u
                // Gain = (Edges currently NOT cut connected to u) - (Edges currently cut connected to u)
                //      = (Neighbors in same set) - (Neighbors in different set)
                int same_set_edges = 0;
                int diff_set_edges = 0;
                
                int my_set = current_partition[u];
                for (int v : adj[u]) {
                    if (current_partition[v] == my_set) {
                        same_set_edges++;
                    } else {
                        diff_set_edges++;
                    }
                }

                int gain = same_set_edges - diff_set_edges;

                // If moving u improves the cut size, do it
                if (gain > 0) {
                    current_partition[u] ^= 1; // Flip 0 <-> 1
                    current_cut += gain;
                    improved = true;
                }
            }

            // If no vertex flip improved the cut, we reached a local maximum
            if (!improved) break;
        }

        // Update global best solution
        if (current_cut > best_cut) {
            best_cut = current_cut;
            best_partition = current_partition;
        }
    }

    // Output the best partition found
    for (int i = 0; i < n; ++i) {
        cout << best_partition[i] << (i == n - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}