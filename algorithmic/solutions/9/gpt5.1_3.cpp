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
        vector<pair<int,int>> edges(n);
        for (int i = 1; i <= n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            edges[i] = {u, v};
            adj[u].push_back({v, i});
            adj[v].push_back({u, i});
        }

        // Permutation psi: vertex v maps to p[v]
        vector<int> psi(n + 1);
        for (int v = 1; v <= n; ++v) psi[v] = p[v];

        // Decompose psi into cycles and convert each cycle into transpositions
        vector<char> vis(n + 1, 0);
        vector<pair<int,int>> macros;
        macros.reserve(n);
        for (int v = 1; v <= n; ++v) {
            if (vis[v]) continue;
            int u = v;
            vector<int> cyc;
            while (!vis[u]) {
                vis[u] = 1;
                cyc.push_back(u);
                u = psi[u];
            }
            if (cyc.size() <= 1) continue;
            int c0 = cyc[0];
            for (size_t j = 1; j < cyc.size(); ++j) {
                macros.push_back({c0, cyc[j]});
            }
        }

        // For each transposition (a,b), realize it by swaps along the unique path between a and b
        vector<int> ops;
        ops.reserve(2 * n * n);
        vector<int> parentV(n + 1), parentE(n + 1);
        vector<int> pathEdges;
        pathEdges.reserve(n);

        for (auto &tr : macros) {
            int a = tr.first;
            int b = tr.second;

            // BFS to find path from a to b
            fill(parentV.begin(), parentV.end(), -1);
            queue<int> q;
            q.push(a);
            parentV[a] = a;
            parentE[a] = 0;
            while (!q.empty()) {
                int x = q.front();
                q.pop();
                if (x == b) break;
                for (auto &pr : adj[x]) {
                    int to = pr.first, eid = pr.second;
                    if (parentV[to] == -1) {
                        parentV[to] = x;
                        parentE[to] = eid;
                        q.push(to);
                    }
                }
            }

            // Reconstruct path edges from a to b
            pathEdges.clear();
            int cur = b;
            while (cur != a) {
                int e = parentE[cur];
                pathEdges.push_back(e);
                cur = parentV[cur];
            }
            reverse(pathEdges.begin(), pathEdges.end());
            int L = (int)pathEdges.size();

            // Forward along path
            for (int i = 0; i < L; ++i) {
                int eid = pathEdges[i];
                ops.push_back(eid);
            }
            // Backward along path excluding the last edge
            for (int i = L - 2; i >= 0; --i) {
                int eid = pathEdges[i];
                ops.push_back(eid);
            }
        }

        cout << ops.size() << '\n';
        for (int eid : ops) {
            cout << 1 << ' ' << eid << '\n';
        }
    }

    return 0;
}