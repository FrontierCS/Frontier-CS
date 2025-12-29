#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>

using namespace std;

const int MAXN = 5005;
vector<int> adj[MAXN];
int parent_node[MAXN];
int depth[MAXN];
bool removed[MAXN];
int sub_sz[MAXN];
int heavy[MAXN];

// Standard DFS to compute depth and parents
void dfs_static(int u, int p, int d) {
    depth[u] = d;
    parent_node[u] = p;
    for (int v : adj[u]) {
        if (v != p) {
            dfs_static(v, u, d + 1);
        }
    }
}

// Compute subtree sizes and heavy children in the current valid tree (ignoring removed nodes)
void dfs_sz(int u) {
    sub_sz[u] = 1;
    heavy[u] = -1;
    int max_s = -1;
    for (int v : adj[u]) {
        if (v != parent_node[u] && !removed[v]) {
            dfs_sz(v);
            sub_sz[u] += sub_sz[v];
            if (sub_sz[v] > max_s) {
                max_s = sub_sz[v];
                heavy[u] = v;
            }
        }
    }
}

// Compute the maximum depth of any valid node in the subtree of u
int max_depth_in_tree(int u) {
    int mx = depth[u];
    for (int v : adj[u]) {
        if (v != parent_node[u] && !removed[v]) {
            mx = max(mx, max_depth_in_tree(v));
        }
    }
    return mx;
}

int query(int u) {
    cout << "? " << u << endl;
    int res;
    cin >> res;
    return res;
}

void solve() {
    int n;
    if (!(cin >> n)) return;
    
    for (int i = 0; i <= n; ++i) {
        adj[i].clear();
        removed[i] = false;
    }

    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    dfs_static(1, 0, 0);

    int curr = 1;
    int current_max_depth_bound = 0;
    for(int i=1; i<=n; ++i) current_max_depth_bound = max(current_max_depth_bound, depth[i]);

    while (true) {
        // If the current node is at the maximum possible depth of the mole, we found it.
        if (depth[curr] == current_max_depth_bound) {
            cout << "! " << curr << endl;
            return;
        }

        // Recompute subtree sizes considering pruned nodes
        dfs_sz(curr);
        
        // Update the depth bound based on the structure of the remaining valid tree
        // The mole cannot be deeper than the deepest valid node in the current subtree
        int subtree_max_depth = max_depth_in_tree(curr);
        current_max_depth_bound = min(current_max_depth_bound, subtree_max_depth);
        
        // Check again after updating bound
        if (depth[curr] == current_max_depth_bound) {
            cout << "! " << curr << endl;
            return;
        }

        // Build the heavy path starting from curr
        vector<int> path;
        int t = curr;
        while (t != -1) {
            path.push_back(t);
            t = heavy[t];
        }

        // Find a node on the heavy path that splits the valid subtree size roughly in half
        int best_u = -1;
        int target = sub_sz[curr] / 2;
        int best_diff = 1e9;
        
        for (int u : path) {
            if (u == curr) continue; 
            int diff = abs(sub_sz[u] - target);
            if (diff < best_diff) {
                best_diff = diff;
                best_u = u;
            }
        }
        
        // If no child is available (should be covered by depth check, but for safety)
        if (best_u == -1) {
             cout << "! " << curr << endl;
             return;
        }

        int res = query(best_u);
        if (res == 1) {
            // Mole is in the subtree of best_u
            curr = best_u;
        } else {
            // Mole is NOT in the subtree of best_u
            removed[best_u] = true;
            // Mole moves up towards the root
            current_max_depth_bound--;
            
            // If we are not at the root, move our current focus up as well to catch the mole if it left curr
            if (curr != 1) curr = parent_node[curr];
            
            // If the current node is deeper than possible, move up
            while (depth[curr] > current_max_depth_bound) {
                curr = parent_node[curr];
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