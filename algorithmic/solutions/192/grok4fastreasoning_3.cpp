#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    vector<vector<int>> adj(n + 1);
    vector<int> deg(n + 1, 0);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        deg[u]++;
        deg[v]++;
    }
    vector<int> side(n + 1, 0);
    vector<int> delta(n + 1, 0);
    for (int v = 1; v <= n; v++) {
        int same = 0;
        for (int u : adj[v]) {
            if (side[u] == side[v]) same++;
        }
        delta[v] = 2 * same - deg[v];
    }
    while (true) {
        bool found = false;
        for (int v = 1; v <= n; v++) {
            if (delta[v] > 0) {
                int old_delta = delta[v];
                int old_side = side[v];
                for (int u : adj[v]) {
                    if (side[u] == old_side) {
                        delta[u] -= 2;
                    } else {
                        delta[u] += 2;
                    }
                }
                side[v] = 1 - old_side;
                delta[v] = -old_delta;
                found = true;
                break;
            }
        }
        if (!found) break;
    }
    for (int i = 1; i <= n; i++) {
        cout << side[i];
        if (i < n) cout << " ";
        else cout << "\n";
    }
    return 0;
}