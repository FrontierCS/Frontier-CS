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

    // Adjacency list for the graph
    // Vertices are 1-indexed in input, so we use size n + 1
    vector<vector<int>> adj(n + 1);
    
    // Store edges to calculate final cut size efficiently
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

    // Random number generator
    // Seed with current time to ensure varied starting points
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    // Best solution found so far
    vector<int> best_s(n + 1, 0);
    long long max_cut = -1;

    // Working solution buffer
    vector<int> s(n + 1);
    // Order vector for iterating vertices
    vector<int> p(n);
    iota(p.begin(), p.end(), 1);

    // Time control
    auto start_time = chrono::high_resolution_clock::now();
    // Set time limit slightly less than typical 1.0s or 2.0s limits to ensure output/cleanup
    // 0.95s is safe for a 1s time limit.
    double time_limit = 0.95; 

    // Helper lambda to calculate cut size of a partition
    auto get_cut_size = [&](const vector<int>& partition) {
        long long c = 0;
        for (const auto& e : edges) {
            if (partition[e.u] != partition[e.v]) {
                c++;
            }
        }
        return c;
    };

    // Main loop: Randomized Restarts Hill Climbing
    while (true) {
        // Check elapsed time
        auto current_time = chrono::high_resolution_clock::now();
        chrono::duration<double> elapsed = current_time - start_time;
        if (elapsed.count() > time_limit) break;

        // Initialize random partition
        for (int i = 1; i <= n; ++i) {
            s[i] = rng() & 1; // Randomly assign 0 or 1
        }

        // Local Search (Hill Climbing)
        // Repeat until we reach a local optimum (1-opt)
        while (true) {
            bool improved = false;
            // Shuffle order of vertices to process to avoid bias
            shuffle(p.begin(), p.end(), rng);

            for (int u : p) {
                int same = 0;
                int diff = 0;
                for (int v : adj[u]) {
                    if (s[u] == s[v]) same++;
                    else diff++;
                }

                // If a vertex has more neighbors in the same set than in the different set,
                // moving it to the other set increases the cut size.
                // Gain = same - diff. If Gain > 0, we flip.
                if (same > diff) {
                    s[u] ^= 1; // Flip 0 <-> 1
                    improved = true;
                }
            }

            // If no vertex can be flipped to improve the cut, stop.
            if (!improved) break;
        }

        // Update global best solution if current is better
        long long current_cut = get_cut_size(s);
        if (current_cut > max_cut) {
            max_cut = current_cut;
            best_s = s;
        }
    }

    // Output result
    for (int i = 1; i <= n; ++i) {
        cout << best_s[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}