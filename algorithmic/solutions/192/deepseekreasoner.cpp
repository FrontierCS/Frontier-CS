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

    // Adjacency list to store the graph
    // Using 1-based indexing for vertices
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Best solution found so far
    // Initialize with all 0s
    vector<int> best_s(n + 1, 0);
    long long max_cut_size = -1;

    // Time management
    // Set a time limit slightly under typical limits (usually 1s or 2s)
    // 0.90 seconds is generally safe for 1s limits
    double time_limit = 0.90;
    auto start_time = chrono::high_resolution_clock::now();

    // Random number generator using steady_clock
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    
    // Processing order vector
    vector<int> p(n);
    iota(p.begin(), p.end(), 1);

    vector<int> current_s(n + 1);

    // Main optimization loop (Randomized Local Search)
    // We run multiple restarts until the time limit is reached
    while (true) {
        // Random initialization of the partition
        for (int i = 1; i <= n; ++i) {
            current_s[i] = rng() & 1;
        }

        // Hill Climbing / Local Search
        // Ideally, in a local optimum, every vertex has at least as many neighbors
        // in the other set as in its own set.
        bool improved = true;
        while (improved) {
            improved = false;
            // Iterate vertices in random order to avoid bias and cycles
            shuffle(p.begin(), p.end(), rng);
            
            for (int u : p) {
                int same_set_neighbors = 0;
                int diff_set_neighbors = 0;
                for (int v : adj[u]) {
                    if (current_s[u] == current_s[v]) {
                        same_set_neighbors++;
                    } else {
                        diff_set_neighbors++;
                    }
                }
                
                // If moving u to the other set increases the number of cut edges
                // (i.e. currently has more neighbors in the same set than the other)
                // then flip it.
                if (same_set_neighbors > diff_set_neighbors) {
                    current_s[u] ^= 1;
                    improved = true;
                }
            }
        }

        // Calculate the cut size for the current stable partition
        long long current_cut = 0;
        for (int u = 1; u <= n; ++u) {
            // Count cut edges: iterate over vertices in set 0 and check neighbors in set 1
            // This counts each cut edge exactly once (from the endpoint in set 0)
            if (current_s[u] == 0) {
                for (int v : adj[u]) {
                    if (current_s[v] == 1) {
                        current_cut++;
                    }
                }
            }
        }

        // Update best solution found
        if (current_cut > max_cut_size) {
            max_cut_size = current_cut;
            best_s = current_s;
        }

        // Check if time limit exceeded
        auto curr_time = chrono::high_resolution_clock::now();
        chrono::duration<double> elapsed = curr_time - start_time;
        if (elapsed.count() > time_limit) break;
    }

    // Output the result
    for (int i = 1; i <= n; ++i) {
        cout << best_s[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}