#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <ctime>
#include <cstdlib>

using namespace std;

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Edge case: no edges
    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            cout << 0 << (i == n ? "" : " ");
        }
        cout << "\n";
        return 0;
    }

    vector<int> best_partition(n + 1, 0);
    int max_cut_edges = -1;

    // Use a timer to perform as many restarts as possible within a safe limit
    clock_t start_time = clock();
    double time_limit = 0.90; // seconds

    vector<int> p(n);
    iota(p.begin(), p.end(), 1); // Fill with 1, 2, ..., n

    srand((unsigned)time(NULL));

    bool first = true;

    while (true) {
        // Check time limit
        if (!first) {
            if ((double)(clock() - start_time) / CLOCKS_PER_SEC > time_limit) break;
        }
        first = false;

        // Random initialization
        vector<int> current_partition(n + 1);
        for (int i = 1; i <= n; ++i) {
            current_partition[i] = rand() & 1;
        }

        // Calculate initial cut size for current_partition
        int current_cut = 0;
        for (int u = 1; u <= n; ++u) {
            for (int v : adj[u]) {
                if (u < v) { // Count undirected edge once
                    if (current_partition[u] != current_partition[v]) {
                        current_cut++;
                    }
                }
            }
        }
        
        // Local Optimization (Hill Climbing)
        bool improved = true;
        while (improved) {
            improved = false;
            
            // Permute check order to avoid bias
            for (int i = n - 1; i > 0; --i) {
                int j = rand() % (i + 1);
                swap(p[i], p[j]);
            }

            for (int u : p) {
                int same = 0;
                int diff = 0;
                // Calculate contribution of u to the cut
                for (int v : adj[u]) {
                    if (current_partition[v] == current_partition[u]) {
                        same++;
                    } else {
                        diff++;
                    }
                }

                // If u has more neighbors in the same set, flip u to improve the cut
                if (same > diff) {
                    current_partition[u] ^= 1; // Flip between 0 and 1
                    current_cut += (same - diff);
                    improved = true;
                }
            }
        }

        // Update global best
        if (current_cut > max_cut_edges) {
            max_cut_edges = current_cut;
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