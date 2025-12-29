#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Global variables to store tree structure
int n;
vector<vector<int>> adj;
vector<int> sz;
vector<int> parent_node;
vector<int> heavy;

// DFS to compute subtree sizes and identify heavy children for HLD
void dfs_sz(int u, int p) {
    sz[u] = 1;
    parent_node[u] = p;
    int max_sz = -1;
    heavy[u] = -1;
    for (int v : adj[u]) {
        if (v != p) {
            dfs_sz(v, u);
            sz[u] += sz[v];
            if (sz[v] > max_sz) {
                max_sz = sz[v];
                heavy[u] = v;
            }
        }
    }
}

// Helper function to perform a query
int query(int x) {
    cout << "? " << x << endl;
    int res;
    cin >> res;
    // -1 indicates invalid query or error in interaction
    if (res == -1) exit(0); 
    return res;
}

void solve() {
    if (!(cin >> n)) return;
    adj.assign(n + 1, vector<int>());
    sz.assign(n + 1, 0);
    parent_node.assign(n + 1, 0);
    heavy.assign(n + 1, -1);

    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Precompute heavy edges
    dfs_sz(1, 0);

    int curr = 1;
    
    // We have a limit of 160 queries.
    // Strategy: HLD-based Binary Search.
    // Maintain 'curr' such that the mole is expected to be in the subtree of 'curr'.
    // In each iteration, construct the heavy path starting from 'curr'.
    // Use binary search on the heavy path to find the deepest node containing the mole.
    
    while (true) {
        // Construct heavy path from curr
        vector<int> path;
        int temp = curr;
        while (temp != -1) {
            path.push_back(temp);
            temp = heavy[temp];
        }

        // If path has only 1 node (curr itself), and since we maintain that mole is in T_curr,
        // the mole must be at curr.
        if (path.size() == 1) {
            cout << "! " << curr << endl;
            return;
        }

        // Binary Search on the heavy path to find the mole
        // We are looking for a node in path[1...end] because we are already at path[0].
        int L = 1; 
        int R = (int)path.size() - 1;
        int fails = 0;
        bool advanced = false;

        // Perform binary search
        while (L <= R) {
            // Bias mid towards the end (deeper nodes). 
            // If we hit 1, we jump deep. If 0, we lose little (mole moves up).
            int mid = (L + R + 1) / 2;
            int res = query(path[mid]);
            
            if (res == 1) {
                // Mole is in the subtree of path[mid].
                // We successfully narrowed down the location significantly.
                curr = path[mid];
                advanced = true;
                break; 
            } else {
                // Mole is NOT in the subtree of path[mid].
                // Mole moves to its parent node.
                // We know mole is above path[mid] (relative to the path structure or off-path).
                R = mid - 1;
                fails++;
            }
        }

        if (!advanced) {
            // We failed to find the mole deeper in the current heavy path.
            // For every failed query (result 0), the mole moved up one step.
            // We need to backtrack 'curr' upwards to maintain the invariant.
            // However, we clamp at the root (node 1).
            int old_curr = curr;
            for (int k = 0; k < fails; ++k) {
                if (curr != 1) {
                    curr = parent_node[curr];
                }
            }
            
            // If we were at the root and tried to find the mole but failed,
            // and after backtracking we remain at the root, then the mole is at the root.
            // (Note: If the mole was in a light child of the root, the query on the heavy child
            // would return 0, causing the mole to move to the root).
            if (curr == 1 && old_curr == 1) {
                cout << "! " << 1 << endl;
                return;
            }
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