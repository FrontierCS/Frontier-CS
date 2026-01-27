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
        vector<vector<pair<int,int>>> adj(n + 1);
        vector<pair<int,int>> edges(n); // 1..n-1
        for (int i = 1; i <= n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back({v, i});
            adj[v].push_back({u, i});
            edges[i] = {u, v};
        }

        vector<int> deg(n + 1, 0);
        vector<char> active(n + 1, 1);
        for (int i = 1; i <= n; ++i) deg[i] = (int)adj[i].size();

        deque<int> leafq;
        for (int i = 1; i <= n; ++i) if (deg[i] <= 1) leafq.push_back(i);

        int activeCnt = n;
        vector<int> swaps; swaps.reserve(n * n / 2 + 5);

        vector<int> parent(n + 1), parentEdge(n + 1);
        vector<char> vis(n + 1);

        while (activeCnt > 1) {
            int u = -1;
            while (!leafq.empty()) {
                int x = leafq.front(); leafq.pop_front();
                if (active[x] && deg[x] <= 1) { u = x; break; }
            }
            if (u == -1) break; // should not happen

            int start = pos[u]; // current position of token u
            if (start != u) {
                // BFS from start to u within active vertices
                fill(vis.begin(), vis.end(), 0);
                queue<int> q;
                q.push(start);
                vis[start] = 1;
                parent[start] = -1;
                parentEdge[start] = -1;
                while (!q.empty() && !vis[u]) {
                    int x = q.front(); q.pop();
                    for (auto [y, eid] : adj[x]) {
                        if (!active[y] || vis[y]) continue;
                        vis[y] = 1;
                        parent[y] = x;
                        parentEdge[y] = eid;
                        if (y == u) break;
                        q.push(y);
                    }
                }
                // reconstruct path nodes from start to u
                vector<int> nodes;
                int cur = u;
                nodes.push_back(cur);
                while (cur != start) {
                    cur = parent[cur];
                    nodes.push_back(cur);
                }
                reverse(nodes.begin(), nodes.end());
                // perform swaps along the path
                for (size_t i = 0; i + 1 < nodes.size(); ++i) {
                    int a = nodes[i], b = nodes[i + 1];
                    int eid = parentEdge[b];
                    swaps.push_back(eid);
                    int ta = p[a], tb = p[b];
                    // swap tokens on vertices a and b
                    p[a] = tb; p[b] = ta;
                    pos[tb] = a; pos[ta] = b;
                }
            }
            // remove leaf u from active tree
            active[u] = 0;
            --activeCnt;
            int par = -1;
            for (auto [v, eid] : adj[u]) {
                if (active[v]) { par = v; break; }
            }
            if (par != -1) {
                --deg[par];
                if (deg[par] == 1) leafq.push_back(par);
            }
            deg[u] = 0;
        }

        cout << swaps.size() << '\n';
        for (int eid : swaps) {
            cout << 1 << ' ' << eid << '\n';
        }
    }
    return 0;
}