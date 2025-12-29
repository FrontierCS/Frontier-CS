#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>

using namespace std;

// Function to query f(u) - Type 1 query
// f(u) is the sum of values on the path from the root to u
int query_f(int u) {
    cout << "? 1 1 " << u << endl;
    int res;
    cin >> res;
    return res;
}

// Function to toggle value of u - Type 2 query
void query_toggle(int u) {
    cout << "? 2 " << u << endl;
}

// Global adjacency list and f values
vector<vector<int>> adj;
vector<int> f_vals;

// Helper function to determine node values assuming a specific root
// Returns an empty vector if the assumption leads to a contradiction (values not 1 or -1)
vector<int> solve_for_root(int root, int n) {
    vector<int> vals(n + 1);
    vector<bool> visited(n + 1, false);
    vector<int> q;
    
    q.push_back(root);
    visited[root] = true;
    
    // For the root, f(root) must be equal to its value.
    // Since values are 1 or -1, |f(root)| must be 1.
    if (abs(f_vals[root]) != 1) return {};
    vals[root] = f_vals[root];

    int head = 0;
    while(head < (int)q.size()){
        int u = q[head++];
        for(int v : adj[u]){
            if(!visited[v]){
                visited[v] = true;
                // If u is parent of v, f(v) = f(u) + val(v) => val(v) = f(v) - f(u)
                int val = f_vals[v] - f_vals[u];
                // Check if the derived value is valid (1 or -1)
                if (abs(val) != 1) return {};
                vals[v] = val;
                q.push_back(v);
            }
        }
    }
    return vals;
}

void solve() {
    int n;
    if (!(cin >> n)) return;
    
    adj.assign(n + 1, vector<int>());
    vector<int> degree(n + 1, 0);
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        degree[u]++;
        degree[v]++;
    }

    f_vals.assign(n + 1, 0);
    vector<bool> known(n + 1, false);

    // Heuristic: Identify the node with the maximum degree.
    // If we skip querying this node, we maximize the chance of deducing its f-value
    // from its neighbors, potentially saving 1 query.
    int skip_node = 1;
    for (int i = 1; i <= n; ++i) {
        if (degree[i] > degree[skip_node]) {
            skip_node = i;
        }
    }

    // Query f(u) for all nodes except the skip_node
    for (int i = 1; i <= n; ++i) {
        if (i == skip_node) continue;
        f_vals[i] = query_f(i);
        known[i] = true;
    }

    // Attempt to deduce f(skip_node)
    // For any neighbor v of u, f(v) = f(u) +/- 1.
    // If u has neighbors with f-values differing by 2 (e.g., X and X+2),
    // then f(u) must be the average (X+1).
    if (n > 1) {
        int min_val = 1000000000, max_val = -1000000000;
        bool has_neighbor = false;
        for (int v : adj[skip_node]) {
            if (known[v]) {
                has_neighbor = true;
                if (f_vals[v] < min_val) min_val = f_vals[v];
                if (f_vals[v] > max_val) max_val = f_vals[v];
            }
        }
        if (has_neighbor && (max_val - min_val == 2)) {
            f_vals[skip_node] = (min_val + max_val) / 2;
            known[skip_node] = true;
        }
    }

    // If deduction failed, we must query the skip_node
    if (!known[skip_node]) {
        f_vals[skip_node] = query_f(skip_node);
        known[skip_node] = true;
    }

    // Generate all valid candidate value configurations by trying each node as root
    vector<vector<int>> candidates;
    for (int r = 1; r <= n; ++r) {
        vector<int> res = solve_for_root(r, n);
        if (!res.empty()) {
            // Check for duplicates before adding
            bool exists = false;
            for(const auto& cand : candidates) {
                if (cand == res) {
                    exists = true;
                    break;
                }
            }
            if (!exists) candidates.push_back(res);
        }
    }

    // Resolve ambiguities if multiple valid configurations exist
    while (candidates.size() > 1) {
        // Find a node index where the candidates disagree on the value
        int diff_node = -1;
        for (int i = 1; i <= n; ++i) {
            int val0 = candidates[0][i];
            for (size_t k = 1; k < candidates.size(); ++k) {
                if (candidates[k][i] != val0) {
                    diff_node = i;
                    goto found_diff;
                }
            }
        }
        found_diff:;
        
        // Toggle the value of that node and measure the new f-value
        // This discriminates between candidates because f(u) changes differently
        // depending on the node's current value.
        query_toggle(diff_node);
        int new_f = query_f(diff_node);
        int old_f = f_vals[diff_node];
        
        // Filter out candidates that are inconsistent with the observed change
        vector<vector<int>> next_candidates;
        for (auto& cand : candidates) {
            int val = cand[diff_node];
            // If we toggle node u with value v, f(u) changes by -2*v
            // because u is always on the path from root to u.
            if (new_f == old_f - 2 * val) {
                // Update the candidate's value for the toggled node
                cand[diff_node] = -val;
                next_candidates.push_back(cand);
            }
        }
        candidates = next_candidates;
        // Update the known f-value for future iterations if needed
        f_vals[diff_node] = new_f; 
    }

    // Output the unique solution
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << candidates[0][i];
    }
    cout << endl;
}

int main() {
    // Interactive problems require careful flushing, but standard cin/cout with endl is safe.
    // Sync off is fine as long as we don't mix C/C++ I/O.
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}