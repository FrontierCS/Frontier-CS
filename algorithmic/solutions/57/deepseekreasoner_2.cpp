#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <cassert>
using namespace std;

int n;
vector<vector<int>> adj;

vector<int> get_parents(int root) {
    vector<int> parent(n+1, -1);
    queue<int> q;
    parent[root] = 0; // dummy parent for root
    q.push(root);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int v : adj[u]) {
            if (parent[v] == -1) {
                parent[v] = u;
                q.push(v);
            }
        }
    }
    return parent;
}

vector<int> compute_values(const vector<int>& f, const vector<int>& parent, int root) {
    vector<int> val(n+1);
    val[root] = f[root];
    for (int i = 1; i <= n; i++) {
        if (i == root) continue;
        val[i] = f[i] - f[parent[i]];
    }
    return val;
}

int main() {
    int t;
    cin >> t;
    while (t--) {
        cin >> n;
        adj.assign(n+1, vector<int>());
        for (int i = 0; i < n-1; i++) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }

        vector<int> f(n+1);
        // query f for each node individually
        for (int i = 1; i <= n; i++) {
            cout << "? 1 1 " << i << endl;
            cin >> f[i];
        }

        // find candidate roots: nodes with f = ±1
        vector<int> candidates;
        for (int i = 1; i <= n; i++) {
            if (abs(f[i]) == 1)
                candidates.push_back(i);
        }

        // compute assignment for first candidate
        int R0 = candidates[0];
        vector<int> parent0 = get_parents(R0);
        vector<int> val0 = compute_values(f, parent0, R0);

        // if only one candidate, we are done
        if (candidates.size() == 1) {
            cout << "! ";
            for (int i = 1; i <= n; i++) {
                cout << val0[i] << " ";
            }
            cout << endl;
            continue;
        }

        // look for another candidate with a different assignment
        int R1 = -1;
        vector<int> val1;
        for (size_t idx = 1; idx < candidates.size(); idx++) {
            int Rc = candidates[idx];
            vector<int> parentc = get_parents(Rc);
            vector<int> valc = compute_values(f, parentc, Rc);
            bool same = true;
            for (int i = 1; i <= n; i++) {
                if (val0[i] != valc[i]) {
                    same = false;
                    break;
                }
            }
            if (!same) {
                R1 = Rc;
                val1 = valc;
                break;
            }
        }

        // if no differing candidate found, all assignments are identical
        if (R1 == -1) {
            cout << "! ";
            for (int i = 1; i <= n; i++) {
                cout << val0[i] << " ";
            }
            cout << endl;
            continue;
        }

        // find a node where the two assignments differ
        int diff_node = -1;
        for (int i = 1; i <= n; i++) {
            if (val0[i] != val1[i]) {
                diff_node = i;
                break;
            }
        }
        assert(diff_node != -1);

        // toggle that node
        cout << "? 2 " << diff_node << endl;
        int dummy;
        cin >> dummy; // read response (unused)

        // query f for that node again
        cout << "? 1 1 " << diff_node << endl;
        int new_f;
        cin >> new_f;

        // compute expected new f under both assignments
        int expected0 = f[diff_node] - 2 * val0[diff_node];
        int expected1 = f[diff_node] - 2 * val1[diff_node];

        vector<int> final_vals(n+1);
        if (new_f == expected0) {
            // R0 is the actual root
            final_vals = val0;
        } else if (new_f == expected1) {
            // R1 is the actual root
            final_vals = val1;
        } else {
            // Should not happen, but fallback to val0
            final_vals = val0;
        }
        // flip the toggled node's value
        final_vals[diff_node] = -final_vals[diff_node];

        cout << "! ";
        for (int i = 1; i <= n; i++) {
            cout << final_vals[i] << " ";
        }
        cout << endl;
    }
    return 0;
}