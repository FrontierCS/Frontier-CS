#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>

using namespace std;

// Global variables
int n;
vector<vector<int>> adj;
vector<int> parent;
vector<int> depth;
vector<bool> removed;
vector<int> subtree_size;
vector<int> subtree_max_depth;

void solve() {
    if (!(cin >> n)) return;
    
    adj.assign(n + 1, vector<int>());
    parent.assign(n + 1, 0);
    depth.assign(n + 1, 0);
    removed.assign(n + 1, false);
    subtree_size.assign(n + 1, 0);
    subtree_max_depth.assign(n + 1, 0);

    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Initialize full tree depths and parents
    auto init_dfs = [&](auto&& self, int u, int p, int d) -> void {
        parent[u] = p;
        depth[u] = d;
        for (int v : adj[u]) {
            if (v != p) {
                self(self, v, u, d + 1);
            }
        }
    };
    init_dfs(init_dfs, 1, 0, 0);

    int max_tree_depth = 0;
    for(int i = 1; i <= n; ++i) max_tree_depth = max(max_tree_depth, depth[i]);
    int limit = max_tree_depth;
    
    int curr = 1;

    while (true) {
        // Compute subtree sizes and max depths for the current valid component rooted at curr
        int current_comp_max_depth = -1;
        
        auto query_dfs = [&](auto&& self, int u) -> void {
            subtree_size[u] = 1;
            subtree_max_depth[u] = depth[u];
            
            for (int v : adj[u]) {
                // Visit children in the original tree that are not removed
                if (depth[v] > depth[u] && !removed[v]) {
                    self(self, v);
                    subtree_size[u] += subtree_size[v];
                    subtree_max_depth[u] = max(subtree_max_depth[u], subtree_max_depth[v]);
                }
            }
        };
        
        query_dfs(query_dfs, curr);
        current_comp_max_depth = subtree_max_depth[curr];
        limit = min(limit, current_comp_max_depth);

        if (limit <= depth[curr]) {
            cout << "! " << curr << endl;
            return;
        }

        // Construct heavy path
        vector<int> heavy_path;
        int temp = curr;
        while (true) {
            heavy_path.push_back(temp);
            int heavy_child = -1;
            int max_sz = -1;
            for (int v : adj[temp]) {
                if (depth[v] > depth[temp] && !removed[v]) {
                    if (subtree_size[v] > max_sz) {
                        max_sz = subtree_size[v];
                        heavy_child = v;
                    }
                }
            }
            if (heavy_child == -1) break;
            temp = heavy_child;
        }

        if (heavy_path.size() <= 1) {
            // Should be covered by limit check, but strictly speaking if only curr remains
            cout << "! " << curr << endl;
            return;
        }

        // Find best split node on heavy path
        // We want sz[node] approx sz[curr] / 2
        int target_sz = subtree_size[curr] / 2;
        int best_node = -1;
        int min_diff = 1e9;

        // Skip the first node (curr), we must query a descendant
        for (size_t i = 1; i < heavy_path.size(); ++i) {
            int u = heavy_path[i];
            int diff = abs(subtree_size[u] - target_sz);
            if (diff < min_diff) {
                min_diff = diff;
                best_node = u;
            }
        }
        
        // As a fallback, if for some reason we didn't pick, pick heavy child
        if (best_node == -1) best_node = heavy_path[1];

        cout << "? " << best_node << endl;
        int res;
        cin >> res;

        if (res == 1) {
            curr = best_node;
        } else {
            // remove subtree
            removed[best_node] = true;
            limit--;
            if (curr != 1) {
                curr = parent[curr];
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