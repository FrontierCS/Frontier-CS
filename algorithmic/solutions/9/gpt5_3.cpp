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

        vector<vector<pair<int,int>>> g(n + 1);
        for (int i = 1; i <= n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            g[u].push_back({v, i});
            g[v].push_back({u, i});
        }

        vector<int> deg(n + 1);
        vector<char> alive(n + 1, 1);
        for (int i = 1; i <= n; ++i) deg[i] = (int)g[i].size();
        int aliveCount = n;

        vector<int> ops;

        while (aliveCount > 0) {
            vector<int> leaves;
            leaves.reserve(aliveCount);
            for (int i = 1; i <= n; ++i) {
                if (alive[i] && deg[i] <= 1) leaves.push_back(i);
            }

            // Swap step: push tokens from leaves inward
            for (int u : leaves) {
                if (!alive[u]) continue;
                if (deg[u] == 0) continue; // isolated node
                if (p[u] == u) continue;   // already correct
                int v = -1, eid = -1;
                for (auto &pr : g[u]) {
                    int w = pr.first, id = pr.second;
                    if (alive[w]) { v = w; eid = id; break; }
                }
                if (v == -1) continue; // no alive neighbor
                swap(p[u], p[v]);
                ops.push_back(eid);
            }

            // Removal step: remove leaves that are correct now
            for (int u : leaves) {
                if (!alive[u]) continue;
                if (p[u] == u) {
                    alive[u] = 0;
                    --aliveCount;
                    for (auto &pr : g[u]) {
                        int w = pr.first;
                        if (alive[w]) --deg[w];
                    }
                    deg[u] = 0;
                }
            }
        }

        cout << ops.size() << '\n';
        for (int e : ops) {
            cout << 1 << ' ' << e << '\n';
        }
    }
    return 0;
}