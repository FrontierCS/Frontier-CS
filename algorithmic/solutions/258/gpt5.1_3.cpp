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

        vector<int> g(n + 1);
        for (int i = 1; i <= n; ++i) {
            cout << "? 1 " << i << '\n';
            cout.flush();
            int x, d;
            if (!(cin >> x >> d)) return 0;
            if (x == -1 && d == -1) return 0;
            g[i] = d;
        }

        int L = *min_element(g.begin() + 1, g.end());
        vector<int> pathNodes;
        vector<int> onPath(n + 1, 0);
        for (int i = 1; i <= n; ++i) {
            if (g[i] == L) {
                pathNodes.push_back(i);
                onPath[i] = 1;
            }
        }

        vector<int> ends;
        for (int v : pathNodes) {
            int cnt = 0;
            for (int to : adj[v]) if (onPath[to]) ++cnt;
            if (cnt == 1) ends.push_back(v);
        }

        int s, f;
        if ((int)ends.size() == 2) {
            s = ends[0];
            f = ends[1];
        } else {
            // Fallback (should not occur under correct conditions)
            if (!pathNodes.empty()) {
                s = pathNodes.front();
                f = pathNodes.back();
            } else {
                s = 1;
                f = 2;
            }
        }

        cout << "! " << s << " " << f << '\n';
        cout.flush();

        string verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict != "Correct") return 0;
    }

    return 0;
}