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
        vector<int> p(n + 1), pos(n + 1);
        for (int i = 1; i <= n; ++i) {
            cin >> p[i];
            pos[p[i]] = i;
        }
        vector<pair<int,int>> edges(n); // 1..n-1 used
        vector<vector<pair<int,int>>> g(n + 1);
        for (int i = 1; i <= n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            edges[i] = {u, v};
            g[u].push_back({v, i});
            g[v].push_back({u, i});
        }

        vector<int> deg(n + 1, 0);
        vector<char> active(n + 1, 1);
        for (int i = 1; i <= n; ++i) deg[i] = (int)g[i].size();

        queue<int> q;
        for (int i = 1; i <= n; ++i) if (deg[i] == 1) q.push(i);

        vector<int> ops; ops.reserve(n * 2); // reserve some; will grow as needed
        int activeCount = n;

        auto get_path_edges = [&](int s, int t) {
            vector<int> prevV(n + 1, -1), prevE(n + 1, -1);
            queue<int> qq;
            prevV[s] = s;
            qq.push(s);
            while (!qq.empty() && prevV[t] == -1) {
                int v = qq.front(); qq.pop();
                for (auto [to, eidx] : g[v]) {
                    if (prevV[to] != -1) continue;
                    if (!active[to] && to != t) continue;
                    prevV[to] = v;
                    prevE[to] = eidx;
                    qq.push(to);
                }
            }
            vector<int> path;
            int cur = t;
            while (cur != s) {
                int eidx = prevE[cur];
                path.push_back(eidx);
                cur = prevV[cur];
            }
            reverse(path.begin(), path.end());
            return path;
        };

        while (activeCount > 1) {
            int u = -1;
            while (!q.empty()) {
                int x = q.front(); q.pop();
                if (active[x] && deg[x] == 1) { u = x; break; }
            }
            if (u == -1) {
                // Should not happen in a tree, but as a safety fallback, pick any active leaf by scan
                for (int i = 1; i <= n; ++i) {
                    if (active[i] && deg[i] == 1) { u = i; break; }
                }
                if (u == -1) break; // safety
            }

            int s = pos[u];
            if (s != u) {
                auto path = get_path_edges(s, u);
                for (int eidx : path) {
                    ops.push_back(eidx);
                    int a = edges[eidx].first, b = edges[eidx].second;
                    int va = p[a], vb = p[b];
                    swap(p[a], p[b]);
                    pos[va] = b;
                    pos[vb] = a;
                }
            }
            // Now p[u] == u
            active[u] = 0;
            --activeCount;
            for (auto [v, eidx] : g[u]) {
                if (active[v]) {
                    deg[v]--;
                    if (deg[v] == 1) q.push(v);
                }
            }
        }

        cout << ops.size() << '\n';
        for (int eidx : ops) {
            cout << 1 << ' ' << eidx << '\n';
        }
    }
    return 0;
}