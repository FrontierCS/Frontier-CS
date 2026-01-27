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
        vector<vector<int>> adj(n + 1);
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }

        vector<long long> D(n + 1);
        long long Dmin = (1LL << 60);

        for (int v = 1; v <= n; ++v) {
            cout << "? 1 " << v << '\n';
            cout.flush();
            int x;
            long long d;
            if (!(cin >> x >> d)) return 0;
            if (x == -1 && d == -1) return 0;
            D[v] = d;
            if (d < Dmin) Dmin = d;
        }

        vector<char> onPath(n + 1, 0);
        for (int v = 1; v <= n; ++v) {
            if (D[v] == Dmin) onPath[v] = 1;
        }

        vector<int> endpoints;
        for (int v = 1; v <= n; ++v) if (onPath[v]) {
            int deg = 0;
            for (int to : adj[v]) if (onPath[to]) ++deg;
            if (deg <= 1) endpoints.push_back(v);
        }

        int s, f;
        if (endpoints.size() == 2) {
            s = endpoints[0];
            f = endpoints[1];
        } else if (endpoints.size() == 1) {
            s = endpoints[0];
            int second = -1;
            for (int to : adj[s]) if (onPath[to]) {
                second = to;
                break;
            }
            if (second == -1) {
                second = (s == 1 ? 2 : 1);
            }
            f = second;
        } else {
            vector<int> pathNodes;
            for (int v = 1; v <= n; ++v) if (onPath[v]) pathNodes.push_back(v);
            int s_candidate = pathNodes.empty() ? 1 : pathNodes[0];

            const int INF = 1e9;
            vector<int> dist(n + 1, INF);
            queue<int> q;
            q.push(s_candidate);
            dist[s_candidate] = 0;
            while (!q.empty()) {
                int u = q.front(); q.pop();
                for (int to : adj[u]) if (onPath[to] && dist[to] == INF) {
                    dist[to] = dist[u] + 1;
                    q.push(to);
                }
            }
            int far = s_candidate;
            for (int v : pathNodes) if (dist[v] > dist[far]) far = v;
            s = s_candidate;
            f = far;
        }

        cout << "! " << s << " " << f << '\n';
        cout.flush();
        string verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict != "Correct") return 0;
    }

    return 0;
}