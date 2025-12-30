#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <set>
#include <map>

using namespace std;

// Function to perform Type 1 query for a single node
int query_f(int u) {
    cout << "? 1 1 " << u << endl;
    int res;
    cin >> res;
    return res;
}

// Function to perform Type 2 query (toggle)
void toggle(int u) {
    cout << "? 2 " << u << endl;
}

// Computes values of all nodes given a hypothesized root and the measured F array
vector<int> solve_vals(int n, int root, const vector<vector<int>>& adj, const vector<int>& F) {
    vector<int> vals(n + 1);
    vector<int> q;
    q.reserve(n);
    q.push_back(root);
    
    vector<bool> visited(n + 1, false);
    visited[root] = true;
    
    vals[root] = F[root];

    int head = 0;
    while(head < q.size()){
        int u = q[head++];
        for(int v : adj[u]){
            if(!visited[v]){
                visited[v] = true;
                // Since u is the parent of v in this rooted configuration:
                // f(v) = f(u) + val(v) => val(v) = f(v) - f(u)
                vals[v] = F[v] - F[u];
                q.push_back(v);
            }
        }
    }
    return vals;
}

void solve() {
    int n;
    if (!(cin >> n)) return;
    
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Measure f(u) for all u. Uses N queries.
    vector<int> F(n + 1);
    for (int i = 1; i <= n; ++i) {
        F[i] = query_f(i);
    }

    // Identify candidate roots. The true root must have |f(root)| == 1.
    vector<int> roots;
    for (int i = 1; i <= n; ++i) {
        if (abs(F[i]) == 1) {
            roots.push_back(i);
        }
    }

    // Generate unique sets of node values implied by each candidate root.
    // Use map to automatically handle duplicates.
    map<vector<int>, vector<int>> val_sets; 
    
    for (int r : roots) {
        vector<int> vals = solve_vals(n, r, adj, F);
        val_sets[vals].push_back(r);
    }

    // If there's only 1 valid assignment of values, output it.
    if (val_sets.size() == 1) {
        const vector<int>& ans = val_sets.begin()->first;
        cout << "!";
        for (int i = 1; i <= n; ++i) cout << " " << ans[i];
        cout << endl;
        return;
    }

    // If there are multiple valid assignments (ambiguity), we must distinguish them.
    // This happens rarely (e.g. monotonic f-values along a line).
    // We pick the first two candidate sets and find a node where they differ.
    auto it = val_sets.begin();
    vector<int> vals1 = it->first;
    it++;
    vector<int> vals2 = it->first;

    int diff_node = -1;
    for (int i = 1; i <= n; ++i) {
        if (vals1[i] != vals2[i]) {
            diff_node = i;
            break;
        }
    }

    // Toggle the differing node. This uses 1 query.
    toggle(diff_node);
    // Measure f(diff_node) again. This uses 1 query.
    int new_f = query_f(diff_node);

    // Check which candidate prediction matches the new measurement.
    // If vals1 was correct, then toggling diff_node changes its value from v to -v.
    // Since diff_node is in the subtree of diff_node (path from root ends at diff_node),
    // f(diff_node) changes by -2 * v.
    // Prediction: new_f = old_f - 2 * vals1[diff_node]
    int pred1 = F[diff_node] - 2 * vals1[diff_node];
    
    cout << "!";
    if (new_f == pred1) {
        // vals1 was the correct initial state.
        // We toggled diff_node, so update the value in our answer.
        vals1[diff_node] *= -1;
        for (int i = 1; i <= n; ++i) cout << " " << vals1[i];
    } else {
        // vals2 was the correct initial state.
        vals2[diff_node] *= -1;
        for (int i = 1; i <= n; ++i) cout << " " << vals2[i];
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while(t--) {
            solve();
        }
    }
    return 0;
}