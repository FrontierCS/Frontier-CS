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

        vector<int> U(n), V(n);
        vector<vector<pair<int,int>>> adj(n + 1);
        vector<int> deg(n + 1, 0);
        for (int i = 1; i <= n - 1; i++) {
            int u, v;
            cin >> u >> v;
            U[i] = u; V[i] = v;
            adj[u].push_back({v, i});
            adj[v].push_back({u, i});
            deg[u]++; deg[v]++;
        }

        vector<char> alive(n + 1, 1);
        int aliveCnt = n;
        queue<int> leaves;
        for (int i = 1; i <= n; i++) if (deg[i] <= 1) leaves.push(i);

        vector<int> ops;
        ops.reserve(n * n / 2);

        vector<int> par(n + 1, -1), parE(n + 1, -1), vis(n + 1, 0);
        int timer = 0;

        auto doSwapEdge = [&](int ei) {
            ops.push_back(ei);
            int a = U[ei], b = V[ei];
            int ta = p[a], tb = p[b];
            swap(p[a], p[b]);
            pos[ta] = b;
            pos[tb] = a;
        };

        while (aliveCnt > 1) {
            int leaf = -1;
            while (!leaves.empty()) {
                int x = leaves.front(); leaves.pop();
                if (alive[x] && deg[x] <= 1) { leaf = x; break; }
            }
            if (leaf == -1) break; // should not happen

            int src = pos[leaf];
            if (src != leaf) {
                timer++;
                queue<int> q;
                q.push(src);
                vis[src] = timer;
                par[src] = src;
                parE[src] = -1;

                while (!q.empty()) {
                    int u = q.front(); q.pop();
                    if (u == leaf) break;
                    for (auto [v, ei] : adj[u]) {
                        if (!alive[v]) continue;
                        if (vis[v] == timer) continue;
                        vis[v] = timer;
                        par[v] = u;
                        parE[v] = ei;
                        q.push(v);
                    }
                }

                vector<int> pathEdges;
                int cur = leaf;
                while (cur != src) {
                    int ei = parE[cur];
                    pathEdges.push_back(ei);
                    cur = par[cur];
                }
                reverse(pathEdges.begin(), pathEdges.end());
                for (int ei : pathEdges) doSwapEdge(ei);
            }

            // remove leaf
            alive[leaf] = 0;
            aliveCnt--;
            for (auto [v, ei] : adj[leaf]) {
                if (!alive[v]) continue;
                deg[v]--;
                if (deg[v] <= 1) leaves.push(v);
            }
            deg[leaf] = 0;
        }

        cout << ops.size() << "\n";
        for (int ei : ops) {
            cout << 1 << " " << ei << "\n";
        }
    }

    return 0;
}