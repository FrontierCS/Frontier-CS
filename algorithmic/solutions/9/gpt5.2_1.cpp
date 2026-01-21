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

        vector<int> p(n + 1), inv(n + 1);
        for (int i = 1; i <= n; i++) {
            cin >> p[i];
            inv[p[i]] = i;
        }

        vector<vector<pair<int,int>>> g(n + 1);
        vector<vector<int>> idx(n + 1, vector<int>(n + 1, 0));

        for (int i = 1; i <= n - 1; i++) {
            int u, v;
            cin >> u >> v;
            g[u].push_back({v, i});
            g[v].push_back({u, i});
            idx[u][v] = idx[v][u] = i;
        }

        vector<char> active(n + 1, 1);
        vector<int> deg(n + 1, 0);
        for (int i = 1; i <= n; i++) deg[i] = (int)g[i].size();

        queue<int> q;
        for (int i = 1; i <= n; i++) if (deg[i] <= 1) q.push(i);

        vector<int> parent(n + 1, -1);
        vector<int> ops;
        ops.reserve(n * n);

        int remaining = n;
        while (remaining > 1) {
            int v = -1;
            while (!q.empty()) {
                int x = q.front(); q.pop();
                if (active[x] && deg[x] <= 1) { v = x; break; }
            }
            if (v == -1) break;

            int pos = inv[v];
            if (pos != v) {
                fill(parent.begin(), parent.end(), -1);
                queue<int> bfs;
                bfs.push(pos);
                parent[pos] = pos;

                while (!bfs.empty() && parent[v] == -1) {
                    int x = bfs.front(); bfs.pop();
                    for (auto [to, eid] : g[x]) {
                        if (!active[to]) continue;
                        if (parent[to] != -1) continue;
                        parent[to] = x;
                        bfs.push(to);
                    }
                }

                vector<int> path;
                int cur = v;
                while (cur != pos) {
                    path.push_back(cur);
                    cur = parent[cur];
                }
                path.push_back(pos);
                reverse(path.begin(), path.end());

                for (int i = 0; i + 1 < (int)path.size(); i++) {
                    int a = path[i], b = path[i + 1];
                    int eid = idx[a][b];
                    ops.push_back(eid);

                    int va = p[a], vb = p[b];
                    swap(p[a], p[b]);
                    inv[va] = b;
                    inv[vb] = a;
                }
            }

            active[v] = 0;
            remaining--;
            for (auto [to, eid] : g[v]) {
                if (!active[to]) continue;
                deg[to]--;
                if (deg[to] <= 1) q.push(to);
            }
            deg[v] = 0;
        }

        cout << ops.size() << '\n';
        for (int eid : ops) {
            cout << 1 << ' ' << eid << '\n';
        }
    }
    return 0;
}