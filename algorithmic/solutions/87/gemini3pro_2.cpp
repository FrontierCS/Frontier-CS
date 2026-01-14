#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>

using namespace std;

const int INF = 1e9;

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    // Read initial coloring
    vector<int> init_state(n);
    for (int i = 0; i < n; ++i) cin >> init_state[i];

    // Read target coloring
    vector<int> target_state(n);
    for (int i = 0; i < n; ++i) cin >> target_state[i];

    // Build graph
    vector<vector<int>> adj(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Compute all-pairs shortest paths using BFS from each node
    // Since edge weights are 1, BFS is sufficient and O(N*(N+M))
    vector<vector<int>> dist(n, vector<int>(n, INF));
    for (int i = 0; i < n; ++i) {
        dist[i][i] = 0;
        queue<int> q;
        q.push(i);
        while (!q.empty()) {
            int u = q.front();
            q.pop();
            for (int v : adj[u]) {
                if (dist[i][v] == INF) {
                    dist[i][v] = dist[i][u] + 1;
                    q.push(v);
                }
            }
        }
    }

    // For each node i, find the best source node p[i]
    // p[i] should satisfy: init_state[p[i]] == target_state[i]
    // We want to minimize dist[i][p[i]]. 
    // If there are ties, pick the one with smallest index (arbitrary consistent rule)
    vector<int> p(n);
    int max_steps = 0;

    for (int i = 0; i < n; ++i) {
        int best_s = -1;
        int min_d = INF;

        for (int s = 0; s < n; ++s) {
            if (init_state[s] == target_state[i]) {
                if (dist[i][s] != INF) {
                     if (dist[i][s] < min_d) {
                        min_d = dist[i][s];
                        best_s = s;
                    }
                }
            }
        }
        // It is guaranteed that a solution exists, so best_s will not be -1
        p[i] = best_s;
        if (min_d > max_steps) max_steps = min_d;
    }

    // Reconstruct the paths from each i to p[i]
    // The path should be a shortest path.
    // path[i] will store the sequence of nodes: i = v_0, v_1, ..., v_k = p[i]
    vector<vector<int>> paths(n);
    for (int i = 0; i < n; ++i) {
        int curr = i;
        paths[i].push_back(curr);
        while (curr != p[i]) {
            int best_neigh = -1;
            // Greedily move to a neighbor closer to p[i]
            for (int v : adj[curr]) {
                if (dist[v][p[i]] != INF && dist[v][p[i]] == dist[curr][p[i]] - 1) {
                    // Tie-break with smallest index to ensure determinism
                    if (best_neigh == -1 || v < best_neigh) {
                        best_neigh = v;
                    }
                }
            }
            curr = best_neigh;
            paths[i].push_back(curr);
        }
    }

    cout << max_steps << "\n";
    
    // Output initial state (step 0)
    for (int i = 0; i < n; ++i) {
        cout << init_state[i] << (i == n - 1 ? "" : " ");
    }
    cout << "\n";

    // Simulate and output states for steps 1 to max_steps
    for (int t = 1; t <= max_steps; ++t) {
        for (int i = 0; i < n; ++i) {
            // At step t, node i takes the value from the t-th node on its path to p[i].
            // If the path length is less than t, it keeps taking from the last node (p[i]),
            // effectively keeping the target color.
            int idx = min(t, (int)paths[i].size() - 1);
            int source_node = paths[i][idx];
            cout << init_state[source_node] << (i == n - 1 ? "" : " ");
        }
        cout << "\n";
    }

    return 0;
}