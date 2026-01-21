#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        cin >> n;
        vector<int> p(n + 1);
        for (int i = 1; i <= n; ++i) cin >> p[i];

        vector<vector<pair<int,int>>> adj(n + 1);
        for (int i = 1; i <= n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back({v, i});
            adj[v].push_back({u, i});
        }

        // Decompose permutation p into transpositions
        vector<pair<int,int>> trans;
        vector<char> vis(n + 1, 0);
        for (int i = 1; i <= n; ++i) {
            if (!vis[i]) {
                int cur = i;
                vector<int> cyc;
                while (!vis[cur]) {
                    vis[cur] = 1;
                    cyc.push_back(cur);
                    cur = p[cur];
                }
                int L = (int)cyc.size();
                if (L > 1) {
                    for (int t = 1; t < L; ++t) {
                        trans.push_back({cyc[0], cyc[t]});
                    }
                }
            }
        }

        vector<int> ops;
        ops.reserve(2 * n * n);

        if (!trans.empty()) {
            vector<int> parent(n + 1), parentEdge(n + 1), q(n + 1);
            for (auto [u_orig, v_orig] : trans) {
                int u = u_orig, v = v_orig;

                // BFS to find path from u to v
                for (int i = 1; i <= n; ++i) parent[i] = -1;
                int head = 0, tail = 0;
                q[tail++] = u;
                parent[u] = 0;
                parentEdge[u] = 0;
                while (head < tail) {
                    int x = q[head++];
                    if (x == v) break;
                    for (auto [to, idx] : adj[x]) {
                        if (parent[to] == -1) {
                            parent[to] = x;
                            parentEdge[to] = idx;
                            q[tail++] = to;
                        }
                    }
                }

                vector<int> path;
                int cur = v;
                while (cur != u) {
                    path.push_back(parentEdge[cur]);
                    cur = parent[cur];
                }
                reverse(path.begin(), path.end());
                int L = (int)path.size();

                // Forward along path
                for (int e : path) ops.push_back(e);
                // Backward along path except last edge
                for (int i = L - 2; i >= 0; --i) ops.push_back(path[i]);
            }
        }

        int m = (int)ops.size();
        cout << m << '\n';
        for (int e : ops) {
            cout << 1 << ' ' << e << '\n';
        }
    }
    return 0;
}