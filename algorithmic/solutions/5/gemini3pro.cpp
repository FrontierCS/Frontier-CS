#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Global variables
int n, m;
vector<int> a(10);
vector<vector<int>> adj;
vector<vector<int>> rev_adj;
vector<int> in_deg_static;
vector<int> out_deg_static;
vector<int> best_path;

// Random engine initialized with time
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

void solve() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return;
    for (int i = 0; i < 10; ++i) cin >> a[i];

    adj.assign(n + 1, vector<int>());
    rev_adj.assign(n + 1, vector<int>());
    in_deg_static.assign(n + 1, 0);
    out_deg_static.assign(n + 1, 0);

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        rev_adj[v].push_back(u);
        out_deg_static[u]++;
        in_deg_static[v]++;
    }

    // Identify forced start node: any node with in-degree 0 MUST be the start
    vector<int> zero_in_nodes;
    for (int i = 1; i <= n; ++i) {
        if (in_deg_static[i] == 0) {
            zero_in_nodes.push_back(i);
        }
    }

    // Candidates for start node if no forced start exists
    vector<int> candidates;
    if (zero_in_nodes.empty()) {
        candidates.resize(n);
        for(int i=0; i<n; ++i) candidates[i] = i + 1;
        // Shuffle first to randomise ties
        shuffle(candidates.begin(), candidates.end(), rng);
        // Sort by in-degree: nodes with lower in-degree are better starts
        sort(candidates.begin(), candidates.end(), [&](int x, int y){
            return in_deg_static[x] < in_deg_static[y];
        });
    }

    // Working arrays for the greedy process
    vector<int> cur_out_deg(n + 1);
    vector<char> visited(n + 1); // vector<char> is faster than vector<bool>
    vector<int> path;
    path.reserve(n);
    vector<int> next_candidates;
    next_candidates.reserve(100);

    auto start_time = chrono::steady_clock::now();
    int cand_idx = 0;
    int run_count = 0;

    // Restart loop until time limit or solution found
    while (true) {
        run_count++;
        // Check time limit periodically (every 32 runs to reduce overhead)
        if ((run_count & 31) == 0) {
            auto now = chrono::steady_clock::now();
            if (chrono::duration_cast<chrono::milliseconds>(now - start_time).count() > 3800) break;
        }

        // If we found a Hamiltonian path, stop immediately
        if ((int)best_path.size() == n) break;

        // Pick start node
        int start_node;
        if (!zero_in_nodes.empty()) {
            // If there's a node with in-degree 0, we must start there.
            // Assuming at most one such node exists due to HP existence guarantee.
            start_node = zero_in_nodes[0];
        } else {
            // Try candidates in sorted order, then random restarts
            if (cand_idx < n) {
                start_node = candidates[cand_idx];
            } else {
                start_node = candidates[rng() % n];
            }
            cand_idx++;
        }

        // Reset state for new run
        for(int i=1; i<=n; ++i) {
            cur_out_deg[i] = out_deg_static[i];
            visited[i] = 0;
        }
        path.clear();

        int curr = start_node;
        visited[curr] = 1;
        path.push_back(curr);

        // Update degrees for neighbors pointing to start node
        for (int prev : rev_adj[curr]) {
            if (!visited[prev]) cur_out_deg[prev]--;
        }

        // Greedy DFS loop using Warnsdorff's Rule
        while (path.size() < n) {
            int best_metric = 2e9;
            next_candidates.clear();

            bool possible = false;
            // Iterate over neighbors
            for (int nxt : adj[curr]) {
                if (!visited[nxt]) {
                    possible = true;
                    int d = cur_out_deg[nxt];
                    // Heuristic: Prefer neighbors with low valid out-degree.
                    // However, avoid degree 0 if possible (dead end), unless it's the only option.
                    int metric = (d == 0 ? 1000000 : d);
                    
                    if (metric < best_metric) {
                        best_metric = metric;
                        next_candidates.clear();
                        next_candidates.push_back(nxt);
                    } else if (metric == best_metric) {
                        next_candidates.push_back(nxt);
                    }
                }
            }

            if (!possible) break;

            // Pick next node
            int next_node;
            if (next_candidates.size() == 1) {
                next_node = next_candidates[0];
            } else {
                // Tie-break randomly
                next_node = next_candidates[rng() % next_candidates.size()];
            }

            curr = next_node;
            visited[curr] = 1;
            path.push_back(curr);
            
            // Update reverse degrees
            for (int prev : rev_adj[curr]) {
                if (!visited[prev]) cur_out_deg[prev]--;
            }
        }

        // Update best path found so far
        if (path.size() > best_path.size()) {
            best_path = path;
        }
    }

    // Output result
    cout << best_path.size() << "\n";
    for (int i = 0; i < (int)best_path.size(); ++i) {
        cout << best_path[i] << (i == (int)best_path.size() - 1 ? "" : " ");
    }
    cout << "\n";
}

int main() {
    solve();
    return 0;
}