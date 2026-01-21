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
        }
        vector<vector<pair<int,int>>> adj(n + 1);
        vector<pair<int,int>> edges(n);
        for (int i = 1; i <= n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            edges[i] = {u, v};
            adj[u].push_back({v, i});
            adj[v].push_back({u, i});
        }
        for (int i = 1; i <= n; ++i) pos[p[i]] = i;

        vector<int> deg(n + 1, 0);
        for (int i = 1; i <= n; ++i) deg[i] = (int)adj[i].size();

        vector<char> alive(n + 1, 1);
        int alive_count = n;
        deque<int> leaves;
        for (int i = 1; i <= n; ++i) if (deg[i] == 1) leaves.push_back(i);

        vector<int> ops;
        vector<int> parent(n + 1), pedge(n + 1);

        while (alive_count > 0) {
            int v = -1;
            while (!leaves.empty()) {
                int t = leaves.front(); leaves.pop_front();
                if (alive[t] && deg[t] == 1) { v = t; break; }
            }
            if (v == -1) {
                if (alive_count == 1) {
                    int last = -1;
                    for (int i = 1; i <= n; ++i) if (alive[i]) { last = i; break; }
                    alive[last] = 0;
                    --alive_count;
                    break;
                } else {
                    // Should not happen in a tree; fallback: find any alive leaf (deg==1) by scan
                    for (int i = 1; i <= n; ++i) {
                        if (alive[i] && deg[i] == 1) { v = i; break; }
                    }
                    if (v == -1) {
                        // If still none, break to avoid infinite loop (theoretically impossible)
                        break;
                    }
                }
            }

            int s = pos[v];
            if (s != v) {
                fill(parent.begin(), parent.end(), -1);
                fill(pedge.begin(), pedge.end(), -1);
                deque<int> q;
                parent[s] = s;
                q.push_back(s);
                while (!q.empty() && parent[v] == -1) {
                    int x = q.front(); q.pop_front();
                    for (auto &pr : adj[x]) {
                        int y = pr.first, e = pr.second;
                        if (!alive[y]) continue;
                        if (parent[y] != -1) continue;
                        parent[y] = x;
                        pedge[y] = e;
                        q.push_back(y);
                        if (y == v) break;
                    }
                }
                vector<int> path_nodes;
                int cur = v;
                path_nodes.push_back(v);
                while (cur != s) {
                    cur = parent[cur];
                    path_nodes.push_back(cur);
                }
                reverse(path_nodes.begin(), path_nodes.end());
                for (size_t i = 0; i + 1 < path_nodes.size(); ++i) {
                    int a = path_nodes[i];
                    int b = path_nodes[i + 1];
                    int e = pedge[b];
                    int x = p[a], y = p[b];
                    p[a] = y; p[b] = x;
                    pos[x] = b; pos[y] = a;
                    ops.push_back(e);
                }
            }
            alive[v] = 0;
            --alive_count;
            for (auto &pr : adj[v]) {
                int to = pr.first;
                if (alive[to]) {
                    --deg[to];
                    if (deg[to] == 1) leaves.push_back(to);
                }
            }
            deg[v] = 0;
        }

        cout << ops.size() << '\n';
        for (int e : ops) {
            cout << 1 << ' ' << e << '\n';
        }
    }
    return 0;
}