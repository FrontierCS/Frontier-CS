#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>

using namespace std;

const int MAXN = 5005;
vector<int> adj[MAXN];
int parent[MAXN];
int depth[MAXN];
int sz[MAXN];
bool blocked[MAXN];
int max_depth_tree;
int cur_max_depth;

void dfs_depth(int u, int p, int d) {
    depth[u] = d;
    parent[u] = p;
    max_depth_tree = max(max_depth_tree, d);
    for (int v : adj[u]) {
        if (v != p) {
            dfs_depth(v, u, d + 1);
        }
    }
}

void calc_sz(int u) {
    sz[u] = 1;
    if (depth[u] > cur_max_depth) {
        sz[u] = 0; // Pruned by depth constraint
        return;
    }
    for (int v : adj[u]) {
        if (v != parent[u] && !blocked[v]) {
            calc_sz(v);
            sz[u] += sz[v];
        }
    }
}

// Function to perform query
int query(int x) {
    cout << "? " << x << endl;
    int res;
    cin >> res;
    return res;
}

void solve() {
    int n;
    if (!(cin >> n)) return;

    for (int i = 1; i <= n; ++i) {
        adj[i].clear();
        blocked[i] = false;
    }

    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    max_depth_tree = 0;
    dfs_depth(1, 0, 0);
    cur_max_depth = max_depth_tree;

    int u = 1;

    while (true) {
        calc_sz(u);

        // If only current node remains (or effective size is small enough to be unique)
        if (sz[u] == 1) {
            cout << "! " << u << endl;
            return;
        }
        
        // If sz[u] == 0, it means the node u itself is deeper than max_depth or invalid.
        // This should not happen if logic is correct, as we reset to 1 which is depth 0.
        // However, robust check:
        if (sz[u] == 0) {
            u = 1; 
            continue;
        }

        // Find heavy path node to query
        int curr = u;
        int target = sz[u] / 2;
        int best_v = -1;

        // Traverse down heavy path
        while (true) {
            int heavy_child = -1;
            int max_s = -1;

            for (int v : adj[curr]) {
                if (v != parent[curr] && !blocked[v] && sz[v] > 0) {
                    if (sz[v] > max_s) {
                        max_s = sz[v];
                        heavy_child = v;
                    }
                }
            }

            if (heavy_child == -1) {
                best_v = curr;
                break;
            }

            if (sz[heavy_child] <= target) {
                best_v = heavy_child;
                break;
            }

            curr = heavy_child;
        }
        
        if (best_v == u) {
            // Should not happen if sz[u] > 1, but if it does, pick heavy child
             int heavy_child = -1;
            int max_s = -1;

            for (int v : adj[u]) {
                if (v != parent[u] && !blocked[v] && sz[v] > 0) {
                    if (sz[v] > max_s) {
                        max_s = sz[v];
                        heavy_child = v;
                    }
                }
            }
            if (heavy_child != -1) best_v = heavy_child;
        }

        int res = query(best_v);
        if (res == 1) {
            u = best_v;
        } else {
            // Mole moved up
            cur_max_depth--;
            blocked[best_v] = true;
            
            if (u == 1) {
                // If we are at root, mole is definitely in subtree of 1 (stays at 1 or moves to 1)
                // Just continue loop, sizes will update
                continue;
            }

            // Verify if mole is still in subtree u
            int res2 = query(u);
            if (res2 == 1) {
                // Mole is still in subtree u
                continue;
            } else {
                // Mole moved out of subtree u
                cur_max_depth--;
                u = 1; // Restart from root
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