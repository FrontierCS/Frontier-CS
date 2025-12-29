#include <bits/stdc++.h>
using namespace std;

int main() {
    int N = 400;
    int M = 1995;
    vector<pair<int, int>> pos(N);
    for (int i = 0; i < N; i++) {
        cin >> pos[i].first >> pos[i].second;
    }
    vector<pair<int, int>> edges(M);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        edges[i] = {u, v};
    }
    vector<int> d(M);
    const int INF = 1e9 + 5;
    for (int i = 0; i < M; i++) {
        int u = edges[i].first, v = edges[i].second;
        int dx = pos[u].first - pos[v].first;
        int dy = pos[u].second - pos[v].second;
        double dist = hypot((double)dx, (double)dy);
        d[i] = (int)round(dist);
    }
    vector<int> parent(N), rnk(N, 0);
    for (int i = 0; i < N; i++) parent[i] = i;
    auto find = [&](auto&& self, int x) -> int {
        if (parent[x] != x) parent[x] = self(self, parent[x]);
        return parent[x];
    };
    auto unite = [&](int x, int y) -> bool {
        int px = find(find, x), py = find(find, y);
        if (px == py) return false;
        if (rnk[px] < rnk[py]) swap(px, py);
        parent[py] = px;
        if (rnk[px] == rnk[py]) rnk[px]++;
        return true;
    };
    for (int i = 0; i < M; i++) {
        int l;
        cin >> l;
        int u = edges[i].first, v = edges[i].second;
        int pu = find(find, u), pv = find(find, v);
        if (pu == pv) {
            cout << 0 << endl;
            fflush(stdout);
            continue;
        }
        // build meta_adj
        vector<vector<int>> meta_adj(N);
        for (int j = i + 1; j < M; j++) {
            int uu = edges[j].first, vv = edges[j].second;
            int cu = find(find, uu), cv = find(find, vv);
            if (cu != cv) {
                meta_adj[cu].push_back(cv);
                meta_adj[cv].push_back(cu);
            }
        }
        // BFS
        vector<bool> vis(N, false);
        queue<int> q;
        q.push(pu);
        vis[pu] = true;
        while (!q.empty()) {
            int c = q.front();
            q.pop();
            for (int nb : meta_adj[c]) {
                if (!vis[nb]) {
                    vis[nb] = true;
                    q.push(nb);
                }
            }
        }
        bool has_alt = vis[pv];
        bool take = !has_alt || ((double)l / d[i] <= 2.0);
        if (take) {
            cout << 1 << endl;
            fflush(stdout);
            unite(u, v);
        } else {
            cout << 0 << endl;
            fflush(stdout);
        }
    }
    return 0;
}