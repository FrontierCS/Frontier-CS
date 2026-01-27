#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <ctime>
#include <numeric>

using namespace std;

int main() {
    // Optimize I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    // Adjacency list using 1-based indexing
    vector<vector<int>> adj(n + 1);
    struct Edge { int u, v; };
    vector<Edge> edges;
    edges.reserve(m);

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.push_back({u, v});
    }

    // Handle case with no edges
    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            cout << 0 << (i == n ? "" : " ");
        }
        cout << "\n";
        return 0;
    }

    // Setup for randomized local search
    mt19937 rng(1337); // Fixed seed for reproducibility/stability
    vector<int> best_partition(n + 1, 0);
    long long max_cut_size = -1;

    // Timer setup (use ~0.95s to stay safely within typical limits)
    clock_t start_time = clock();
    double time_limit = 0.95;

    // Buffers for computation
    vector<int> current_partition(n + 1);
    vector<int> order(n);
    iota(order.begin(), order.end(), 1);

    // Run repeatedly until time runs out
    while (true) {
        double elapsed = (double)(clock() - start_time) / CLOCKS_PER_SEC;
        if (elapsed > time_limit) break;

        // Initialize with a random partition
        for (int i = 1; i <= n; ++i) {
            current_partition[i] = rng() % 2;
        }

        // Local Search (Hill Climbing)
        bool improved = true;
        while (improved) {
            improved = false;
            // Process vertices in random order to avoid bias
            shuffle(order.begin(), order.end(), rng);

            for (int u : order) {
                int d0 = 0; // Neighbors in set 0
                int d1 = 0; // Neighbors in set 1
                for (int v : adj[u]) {
                    if (current_partition[v] == 0) d0++;
                    else d1++;
                }

                // Calculate gain if we move vertex u to the other set
                // We want to maximize edges to the OTHER set.
                // If u is in 0, edges cut = d1. Moving to 1 makes edges cut = d0.
                // Gain = d0 - d1.
                int gain = 0;
                if (current_partition[u] == 0) {
                    gain = d0 - d1;
                } else { // current_partition[u] == 1
                    gain = d1 - d0;
                }

                if (gain > 0) {
                    current_partition[u] ^= 1; // Flip set
                    improved = true;
                }
            }
        }

        // Calculate score for the converged partition
        long long current_cut = 0;
        for (const auto& e : edges) {
            if (current_partition[e.u] != current_partition[e.v]) {
                current_cut++;
            }
        }

        // Update best solution found
        if (current_cut > max_cut_size) {
            max_cut_size = current_cut;
            best_partition = current_partition;
        }
    }

    // Output the best partition found
    for (int i = 1; i <= n; ++i) {
        cout << best_partition[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}