#include <iostream>
#include <vector>
#include <algorithm>
#include <functional>

using namespace std;

int query(int x) {
    cout << "? " << x << endl;
    int res;
    cin >> res;
    return res;
}

void answer(int x) {
    cout << "! " << x << endl;
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

    if (n == 1) {
        answer(1);
        return;
    }

    vector<int> sz(n + 1);
    vector<int> par(n + 1);
    // Re-root at 1 and compute sizes
    function<void(int, int)> dfs = [&](int u, int p) {
        sz[u] = 1;
        par[u] = p;
        // Remove parent from adj to handle as directed tree
        for (auto it = adj[u].begin(); it != adj[u].end(); ) {
            if (*it == p) {
                it = adj[u].erase(it);
            } else {
                dfs(*it, u);
                sz[u] += sz[*it];
                ++it;
            }
        }
        // Sort children by size descending
        sort(adj[u].begin(), adj[u].end(), [&](int a, int b) {
            return sz[a] > sz[b];
        });
    };

    dfs(1, 0);

    vector<int> ptr(n + 1, 0);
    int u = 1;
    
    // limit for the current heavy path search.
    // Effectively, we only search up to path index 'limit'.
    // Initialized to N (infinity).
    int limit = n + 1;

    while (true) {
        // Construct heavy path from u using valid children
        // path[0] = u
        vector<int> path;
        int curr = u;
        path.push_back(curr);
        
        while (ptr[curr] < adj[curr].size()) {
            curr = adj[curr][ptr[curr]];
            path.push_back(curr);
        }

        // If path has only u, we exhausted children, so mole is at u
        if (path.size() == 1) {
            answer(u);
            return;
        }

        // Determine target on path
        // Use binary search approach: target middle of valid range
        // Valid range on path is indices 1 to min(path.size()-1, limit)
        // Note: index 0 is u. We shouldn't query u unless necessary.
        
        int eff_len = (int)path.size();
        if (eff_len > limit + 1) eff_len = limit + 1;
        
        // We want to query a node. If we pick index k:
        // range becomes [k, eff_len-1] (if 1) -> u jumps to p[k]
        // range becomes [0, k-1] (if 0 and still in u) -> limit becomes k-1
        
        // Pick middle
        int k = eff_len / 2;
        // Ensure k >= 1
        if (k < 1) k = 1;
        
        int v = path[k];
        int res = query(v);

        if (res == 1) {
            u = v;
            limit = n + 1; // Reset limit as we moved down
        } else {
            // Mole moves up.
            // Check if mole is still in u.
            // Exception: if u==1, mole is always in u (1) if it's in the tree.
            // But we need to know if we should prune the child.
            // With u=1, if we query 1, we get 1.
            // So we treat it same as query(u) == 1.
            
            bool in_u = true;
            if (u != 1) {
                int r2 = query(u);
                if (r2 == 0) {
                    in_u = false;
                }
            }
            
            if (!in_u) {
                // Mole moved out of u
                // We must ban u from parent's list if possible
                int child = u;
                u = par[u];
                limit = n + 1; // Reset limit
                
                // Ban child from u
                // Since adj is sorted, child should be at ptr[u]
                // but strictly speaking we should check
                if (ptr[u] < adj[u].size() && adj[u][ptr[u]] == child) {
                    ptr[u]++;
                }
            } else {
                // Mole in u, but not in v
                // Reduce limit
                limit = k - 1;
                if (limit == 0) {
                    // We eliminated the current heavy child
                    ptr[u]++;
                    limit = n + 1;
                }
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