#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <ctime>

using namespace std;

int main() {
    // optimize I/O operations
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

    // We use a randomized local search heuristic.
    // Start with a random partition and greedily flip vertices if it improves the cut.
    // Repeat with new random initializations until time runs out.
    
    vector<int> best_partition(n + 1, 0);
    long long max_cut = -1;

    // Use a fixed seed for reproducibility, or random device for diversity.
    // Given the greedy nature, a fixed high-quality RNG is sufficient.
    mt19937 rng(239);

    // Indices for shuffling order
    vector<int> p(n);
    for (int i = 0; i < n; ++i) p[i] = i + 1;

    clock_t start_time = clock();
    double time_limit = 0.90; // seconds

    bool first_iteration = true;

    while (first_iteration || (double)(clock() - start_time) / CLOCKS_PER_SEC < time_limit) {
        first_iteration = false;

        vector<int> current_partition(n + 1);
        // Random initialization
        for (int i = 1; i <= n; ++i) {
            current_partition[i] = rng() % 2;
        }

        // Local search to convergence (Local Optimum)
        bool improved = true;
        while (improved) {
            improved = false;
            // Process vertices in random order to avoid bias
            shuffle(p.begin(), p.end(), rng);
            
            for (int u : p) {
                int same_set_neighbors = 0;
                for (int v : adj[u]) {
                    if (current_partition[v] == current_partition[u]) {
                        same_set_neighbors++;
                    }
                }

                // If more than half neighbors are in the same set, moving u
                // to the other set increases the number of cut edges.
                // Condition: same > diff  <=>  2 * same > total
                if (2 * same_set_neighbors > (int)adj[u].size()) {
                    current_partition[u] ^= 1; // Flip 0->1 or 1->0
                    improved = true;
                }
            }
        }

        // Calculate cut size for this local optimum
        long long current_cut_val = 0;
        for (int i = 1; i <= n; ++i) {
            if (current_partition[i] == 0) {
                for (int v : adj[i]) {
                    if (current_partition[v] == 1) {
                        current_cut_val++;
                    }
                }
            }
        }

        if (current_cut_val > max_cut) {
            max_cut = current_cut_val;
            best_partition = current_partition;
        }
        
        // If we achieved the maximum possible cut (all edges), break early
        if (max_cut == m && m > 0) break;
    }

    // Output the best partition found
    for (int i = 1; i <= n; ++i) {
        cout << best_partition[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}