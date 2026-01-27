#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Structure to store edge information for final scoring
struct Edge {
    int u, v;
};

int main() {
    // Optimize I/O operations for performance
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    // Adjacency list for the graph
    vector<vector<int>> adj(n + 1);
    // Store edges to easily calculate cut size later
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

    // Initialize random number generator with a time-based seed
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    vector<int> best_partition(n + 1);
    long long max_cut = -1;

    // We use a local search strategy (Greedy Hill Climbing) with random restarts.
    // Given N <= 1000 and M <= 20000, the local search is very efficient.
    // 50 restarts is typically sufficient to find a very good approximation 
    // and runs well within standard time limits.
    int restarts = 50; 
    
    // Permutation vector for traversing nodes in random order to avoid bias
    vector<int> p(n);
    iota(p.begin(), p.end(), 1);

    for (int r = 0; r < restarts; ++r) {
        vector<int> current_partition(n + 1);
        
        // Random initialization of the partition
        for (int i = 1; i <= n; ++i) {
            current_partition[i] = rng() % 2;
        }

        // Hill Climbing: repeatedly improve the solution until local optimum
        bool improved = true;
        while (improved) {
            improved = false;
            // Shuffle processing order to avoid cyclic behavior
            shuffle(p.begin(), p.end(), rng);
            
            for (int u : p) {
                int d_same = 0;
                int d_diff = 0;
                // Calculate number of neighbors in same set vs different set
                for (int v : adj[u]) {
                    if (current_partition[v] == current_partition[u]) {
                        d_same++;
                    } else {
                        d_diff++;
                    }
                }

                // If moving vertex u to the other set increases the number of cut edges
                // (i.e., decreases edges within the same set), perform the move.
                if (d_same > d_diff) {
                    current_partition[u] ^= 1;
                    improved = true;
                }
            }
        }

        // Calculate final cut size for this restart
        long long current_cut = 0;
        for (const auto& e : edges) {
            if (current_partition[e.u] != current_partition[e.v]) {
                current_cut++;
            }
        }

        // Update best solution found so far
        if (current_cut > max_cut) {
            max_cut = current_cut;
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