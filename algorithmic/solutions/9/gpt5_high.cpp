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
        vector<int> p(n + 1), val(n + 1), pos(n + 1);
        for (int i = 1; i <= n; ++i) {
            cin >> p[i];
            val[i] = p[i];
            pos[p[i]] = i;
        }
        vector<pair<int,int>> edges(n); // 1..n-1 used
        vector<vector<pair<int,int>>> adj(n + 1);
        vector<int> deg(n + 1, 0), degActive(n + 1, 0);
        for (int i = 1; i <= n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            edges[i] = {u, v};
            adj[u].push_back({v, i});
            adj[v].push_back({u, i});
            deg[u]++; deg[v]++;
        }
        degActive = deg;
        vector<char> removed(n + 1, 0);
        int activeCnt = n;
        queue<int> q;
        for (int i = 1; i <= n; ++i) if (degActive[i] <= 1) q.push(i);

        vector<int> opsEdges;

        while (activeCnt > 1) {
            int u = -1;
            while (!q.empty()) {
                int x = q.front(); q.pop();
                if (!removed[x] && degActive[x] == 1) { u = x; break; }
            }
            if (u == -1) {
                for (int i = 1; i <= n; ++i) {
                    if (!removed[i] && degActive[i] == 1) { u = i; break; }
                }
            }
            if (u == -1) break; // should not happen in a tree

            if (val[u] != u) {
                int start = pos[u];
                if (start != u) {
                    vector<int> parent(n + 1, -1);
                    vector<int> pEdge(n + 1, -1);
                    queue<int> qb;
                    qb.push(start);
                    parent[start] = start;
                    while (!qb.empty() && parent[u] == -1) {
                        int x = qb.front(); qb.pop();
                        for (auto [y, ei] : adj[x]) {
                            if (removed[y]) continue;
                            if (parent[y] != -1) continue;
                            parent[y] = x;
                            pEdge[y] = ei;
                            qb.push(y);
                        }
                    }
                    // reconstruct path vertices from start to u
                    vector<int> pathVrev;
                    int cur = u;
                    while (true) {
                        pathVrev.push_back(cur);
                        if (cur == start) break;
                        cur = parent[cur];
                    }
                    vector<int> pathV(pathVrev.rbegin(), pathVrev.rend());
                    for (size_t t = 0; t + 1 < pathV.size(); ++t) {
                        int a = pathV[t], b = pathV[t + 1];
                        int eindex = pEdge[b]; // parent[b] == a
                        int tokenA = val[a], tokenB = val[b];
                        swap(val[a], val[b]);
                        pos[tokenA] = b;
                        pos[tokenB] = a;
                        opsEdges.push_back(eindex);
                    }
                }
            }
            // remove u
            removed[u] = 1;
            activeCnt--;
            int neighbor = -1, cnt = 0;
            for (auto [v, ei] : adj[u]) {
                if (!removed[v]) { neighbor = v; cnt++; }
            }
            if (cnt == 1) {
                degActive[neighbor]--;
                if (degActive[neighbor] == 1) q.push(neighbor);
            }
            degActive[u] = 0;
        }

        cout << (int)opsEdges.size() << '\n';
        for (int e : opsEdges) {
            cout << 1 << ' ' << e << '\n';
        }
    }
    return 0;
}