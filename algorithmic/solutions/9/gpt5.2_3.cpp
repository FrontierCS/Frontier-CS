#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    cin >> T;
    while (T--) {
        int n;
        cin >> n;

        vector<int> p(n + 1), pos(n + 1);
        for (int i = 1; i <= n; i++) {
            cin >> p[i];
            pos[p[i]] = i;
        }

        vector<vector<pair<int,int>>> adj(n + 1);
        for (int i = 1; i <= n - 1; i++) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back({v, i});
            adj[v].push_back({u, i});
        }

        vector<int> deg(n + 1, 0);
        for (int i = 1; i <= n; i++) deg[i] = (int)adj[i].size();

        vector<char> removed(n + 1, 0);
        queue<int> q;
        for (int i = 1; i <= n; i++) if (deg[i] <= 1) q.push(i);

        vector<int> ops; // each op is a single edge swap
        ops.reserve(n * n / 2 + 5);

        vector<int> parent(n + 1, 0), parentEdge(n + 1, 0), vis(n + 1, 0);
        int iter = 0;

        int remaining = n;
        while (remaining > 1) {
            int v;
            while (true) {
                v = q.front(); q.pop();
                if (!removed[v] && deg[v] <= 1) break;
            }

            if (p[v] != v) {
                int s = pos[v];

                ++iter;
                deque<int> dq;
                dq.push_back(v);
                vis[v] = iter;
                parent[v] = 0;
                parentEdge[v] = 0;

                while (!dq.empty()) {
                    int x = dq.front();
                    dq.pop_front();
                    if (x == s) break;
                    for (auto [to, eid] : adj[x]) {
                        if (removed[to] || vis[to] == iter) continue;
                        vis[to] = iter;
                        parent[to] = x;
                        parentEdge[to] = eid;
                        dq.push_back(to);
                    }
                }

                int cur = s;
                while (cur != v) {
                    int par = parent[cur];
                    int eid = parentEdge[cur];

                    ops.push_back(eid);

                    int a = p[cur], b = p[par];
                    swap(p[cur], p[par]);
                    pos[a] = par;
                    pos[b] = cur;

                    cur = par;
                }
            }

            removed[v] = 1;
            remaining--;

            // update degree of the only remaining neighbor (if any)
            for (auto [to, eid] : adj[v]) {
                if (removed[to]) continue;
                deg[to]--;
                if (deg[to] <= 1) q.push(to);
                break;
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