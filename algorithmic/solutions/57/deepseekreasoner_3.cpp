#include <bits/stdc++.h>
using namespace std;

const int MAXN = 1005;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int t;
    cin >> t;
    while (t--) {
        int n;
        cin >> n;
        vector<vector<int>> adj(n+1);
        for (int i = 0; i < n-1; i++) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }

        // Query f[u] for every node
        vector<int> f(n+1);
        for (int u = 1; u <= n; u++) {
            cout << "? 1 1 " << u << endl;
            cout.flush();
            cin >> f[u];
        }

        // Precompute parent and subtree size for every possible root
        vector<vector<int>> parent(n+1, vector<int>(n+1, 0));
        vector<vector<int>> subsize(n+1, vector<int>(n+1, 0));
        for (int r = 1; r <= n; r++) {
            function<void(int,int)> dfs = [&](int u, int p) {
                parent[r][u] = p;
                subsize[r][u] = 1;
                for (int v : adj[u]) {
                    if (v == p) continue;
                    dfs(v, u);
                    subsize[r][u] += subsize[r][v];
                }
            };
            dfs(r, 0);
        }

        // Try each node as root, compute candidate assignments
        struct Candidate {
            int root;
            vector<int> a;
        };
        vector<Candidate> candidates;
        for (int r = 1; r <= n; r++) {
            vector<int> a(n+1);
            a[r] = f[r];
            bool ok = true;
            for (int u = 1; u <= n; u++) {
                if (u == r) continue;
                int p = parent[r][u];
                a[u] = f[u] - f[p];
                if (a[u] != 1 && a[u] != -1) {
                    ok = false;
                    break;
                }
            }
            if (ok) {
                candidates.push_back({r, a});
            }
        }

        // If only one candidate, output its assignment
        if (candidates.size() == 1) {
            cout << "!";
            for (int i = 1; i <= n; i++) {
                cout << " " << candidates[0].a[i];
            }
            cout << endl;
            cout.flush();
            continue;
        }

        // Check if all candidates give the same assignment
        bool same = true;
        for (size_t i = 1; i < candidates.size(); i++) {
            if (candidates[i].a != candidates[0].a) {
                same = false;
                break;
            }
        }
        if (same) {
            cout << "!";
            for (int i = 1; i <= n; i++) {
                cout << " " << candidates[0].a[i];
            }
            cout << endl;
            cout.flush();
            continue;
        }

        // Find a node where assignments differ
        int x = -1;
        for (int i = 1; i <= n; i++) {
            int val0 = candidates[0].a[i];
            for (size_t j = 1; j < candidates.size(); j++) {
                if (candidates[j].a[i] != val0) {
                    x = i;
                    break;
                }
            }
            if (x != -1) break;
        }
        // Toggle node x
        cout << "? 2 " << x << endl;
        cout.flush();
        // No response to read for type 2

        // Query total sum of f after toggle
        cout << "? 1 " << n;
        for (int i = 1; i <= n; i++) {
            cout << " " << i;
        }
        cout << endl;
        cout.flush();
        int S2;
        cin >> S2;
        int S = accumulate(f.begin()+1, f.end(), 0);
        int delta = S2 - S;

        // Determine which candidate matches the delta
        int true_idx = -1;
        for (size_t idx = 0; idx < candidates.size(); idx++) {
            int r = candidates[idx].root;
            int a_x = candidates[idx].a[x];
            int sz = subsize[r][x];
            int pred = -2 * a_x * sz;
            if (pred == delta) {
                true_idx = idx;
                break;
            }
        }
        // In case of multiple matches (unlikely), pick the first
        if (true_idx == -1) true_idx = 0;

        // Output final values (after toggle on x)
        cout << "!";
        for (int i = 1; i <= n; i++) {
            int val = candidates[true_idx].a[i];
            if (i == x) val = -val;  // because we toggled x
            cout << " " << val;
        }
        cout << endl;
        cout.flush();
    }
    return 0;
}