#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        vector<vector<int>> g(n + 1);
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            g[u].push_back(v);
            g[v].push_back(u);
        }

        vector<long long> f(n + 1, 0);
        for (int u = 1; u <= n; ++u) {
            cout << "? 1 1 " << u << '\n';
            cout.flush();
            long long x;
            if (!(cin >> x)) return 0;
            f[u] = x;
        }

        vector<int> par(n + 1, 0), order;
        order.reserve(n);
        queue<int> q;
        q.push(1);
        par[1] = -1;
        order.push_back(1);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : g[u]) {
                if (v == par[u]) continue;
                par[v] = u;
                q.push(v);
                order.push_back(v);
            }
        }

        vector<int> s(n + 1, 1);
        s[1] = (f[1] >= 0 ? 1 : -1);
        for (int i = 1; i < (int)order.size(); ++i) {
            int u = order[i];
            int p = par[u];
            long long diff = f[u] - f[p];
            if (diff == 0) diff = 1; // fallback
            s[u] = (diff > 0 ? 1 : -1);
        }

        cout << "!"; 
        for (int i = 1; i <= n; ++i) cout << ' ' << s[i];
        cout << '\n';
        cout.flush();
    }
    return 0;
}