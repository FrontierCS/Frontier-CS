#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Timer class to manage execution time limit
class Timer {
    using clock_type = chrono::high_resolution_clock;
    clock_type::time_point start_time;
    double limit;

public:
    Timer(double limit_sec) : limit(limit_sec) {
        start_time = clock_type::now();
    }

    bool time_up() {
        auto current_time = clock_type::now();
        chrono::duration<double> elapsed = current_time - start_time;
        return elapsed.count() >= limit;
    }
};

int main() {
    // Optimize standard I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    if (!(cin >> n >> m)) return 0;

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

    // Random number generator setup
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    vector<int> best_partition(n + 1, 0);
    long long max_cut_size = -1;

    // Use ~0.95 seconds to fit within typical 1.0s or 2.0s competitive programming limits
    Timer timer(0.95);

    vector<int> current_partition(n + 1);
    vector<int> nodes(n);
    iota(nodes.begin(), nodes.end(), 1);

    // Repeatedly perform Randomized Local Search (Hill Climbing)
    while (!timer.time_up()) {
        // 1. Random initialization
        for (int i = 1; i <= n; ++i) {
            current_partition[i] = rng() & 1; // 0 or 1
        }

        // 2. Calculate initial cut size for this configuration
        long long current_cut = 0;
        for (const auto& e : edges) {
            if (current_partition[e.u] != current_partition[e.v]) {
                current_cut++;
            }
        }

        // 3. Improve the solution greedily
        bool improved = true;
        while (improved) {
            improved = false;
            shuffle(nodes.begin(), nodes.end(), rng); // Process nodes in random order

            for (int u : nodes) {
                // Calculate gain if we flip vertex u:
                // Gain = (neighbors in same set) - (neighbors in different set)
                // If we flip, 'same' becomes 'different' (adding to cut) 
                // and 'different' becomes 'same' (removing from cut).
                
                int d_same = 0;
                int d_diff = 0;
                
                for (int v : adj[u]) {
                    if (current_partition[u] == current_partition[v]) {
                        d_same++;
                    } else {
                        d_diff++;
                    }
                }

                int gain = d_same - d_diff;
                
                if (gain > 0) {
                    current_partition[u] ^= 1; // Flip 0 <-> 1
                    current_cut += gain;
                    improved = true;
                }
            }
        }

        // 4. Update global maximum
        if (current_cut > max_cut_size) {
            max_cut_size = current_cut;
            best_partition = current_partition;
        }
    }

    // Output result
    for (int i = 1; i <= n; ++i) {
        cout << best_partition[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}