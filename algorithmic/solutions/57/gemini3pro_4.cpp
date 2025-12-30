#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <map>

using namespace std;

int n;
vector<vector<int>> adj;
vector<int> f_values;
bool f_known[1005];

// Type 1 query: sum of f(u) for u in nodes
int query_type1(const vector<int>& nodes) {
    if (nodes.empty()) return 0;
    cout << "? 1 " << nodes.size();
    for (int u : nodes) cout << " " << u;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

// Type 2 query: toggle value of u
void query_type2(int u) {
    cout << "? 2 " << u << endl;
    // No output to read
}

void solve() {
    cin >> n;
    adj.assign(n + 1, vector<int>());
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Bipartite coloring to split nodes into two sets
    vector<int> color(n + 1, 0);
    vector<int> setA, setB;
    vector<int> q_bfs;
    q_bfs.push_back(1);
    color[1] = 1;
    setA.push_back(1);
    
    int head = 0;
    while(head < q_bfs.size()){
        int u = q_bfs[head++];
        for(int v : adj[u]){
            if(color[v] == 0){
                color[v] = 3 - color[u];
                if(color[v] == 1) setA.push_back(v);
                else setB.push_back(v);
                q_bfs.push_back(v);
            }
        }
    }

    f_values.assign(n + 1, 0);
    for(int i=0; i<=n; ++i) f_known[i] = false;

    // Query all nodes in setA
    for (int u : setA) {
        vector<int> q = {u};
        f_values[u] = query_type1(q);
        f_known[u] = true;
    }

    // Process setB
    // For each node in setB, check its neighbors (which are all in setA and thus known).
    // If we find neighbors with different f_values (diff must be 2), we can deduce f[u].
    // Otherwise, we must query.
    for (int u : setB) {
        int min_val = 1e9, max_val = -1e9;
        for (int v : adj[u]) {
            if (f_known[v]) {
                min_val = min(min_val, f_values[v]);
                max_val = max(max_val, f_values[v]);
            }
        }
        
        // Neighbors f-values must differ by exactly 2 if they differ (same parity)
        if (max_val - min_val == 2) {
            f_values[u] = (min_val + max_val) / 2;
            f_known[u] = true;
        } else {
            // Can't deduce, query it
            vector<int> q = {u};
            f_values[u] = query_type1(q);
            f_known[u] = true;
        }
    }

    // Structure to hold potential solutions
    struct Solution {
        int root;
        vector<int> vals;
        bool operator<(const Solution& other) const {
            return vals < other.vals;
        }
        bool operator==(const Solution& other) const {
            return vals == other.vals;
        }
    };

    // Helper to generate values given a root candidate
    auto get_solution = [&](int root) -> pair<bool, vector<int>> {
        vector<int> vals(n + 1);
        if (abs(f_values[root]) != 1) return {false, {}};
        
        // BFS to determine values
        vector<int> q;
        q.push_back(root);
        vector<int> visited(n + 1, 0);
        visited[root] = 1;
        vals[root] = f_values[root];

        int h = 0;
        while(h < q.size()){
            int u = q[h++];
            for(int v : adj[u]){
                if(!visited[v]){
                    visited[v] = 1;
                    int val = f_values[v] - f_values[u];
                    if(abs(val) != 1) return {false, {}}; // Should not happen if data consistent
                    vals[v] = val;
                    q.push_back(v);
                }
            }
        }
        return {true, vals};
    };

    vector<Solution> solutions;
    for (int r = 1; r <= n; ++r) {
        pair<bool, vector<int>> res = get_solution(r);
        if (res.first) {
            solutions.push_back({r, res.second});
        }
    }

    // Filter unique value assignments
    sort(solutions.begin(), solutions.end());
    auto last = unique(solutions.begin(), solutions.end());
    solutions.erase(last, solutions.end());

    if (solutions.size() == 1) {
        cout << "!";
        for (int i = 1; i <= n; ++i) cout << " " << solutions[0].vals[i];
        cout << endl;
        return;
    }

    // If ambiguity remains, distinguish by toggling a node where solutions differ.
    // Pick the first node with different values across solutions.
    int diff_node = -1;
    for (int i = 1; i <= n; ++i) {
        int val = solutions[0].vals[i];
        for (size_t k = 1; k < solutions.size(); ++k) {
            if (solutions[k].vals[i] != val) {
                diff_node = i;
                break;
            }
        }
        if (diff_node != -1) break;
    }

    // Toggle diff_node and query f(diff_node) again
    query_type2(diff_node);
    int new_f = query_type1({diff_node});

    // Check which solution is consistent with the new f value
    for (const auto& sol : solutions) {
        // With root `sol.root`, f(diff_node) changes by -2 * v_old
        // f_new = f_old - 2 * v_old
        int expected_new_f = f_values[diff_node] - 2 * sol.vals[diff_node];
        if (expected_new_f == new_f) {
            // Found the correct solution. Note: values are now changed!
            // We need to output the CURRENT values (after toggle).
            // Current value of diff_node is -v_old. Others unchanged.
            cout << "!";
            for (int i = 1; i <= n; ++i) {
                int val = sol.vals[i];
                if (i == diff_node) val = -val;
                cout << " " << val;
            }
            cout << endl;
            return;
        }
    }
}

int main() {
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