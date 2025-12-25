#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
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
    vector<int> order(n);
    iota(order.begin(), order.end(), 1);
    sort(order.begin(), order.end(), [&](int a, int b) {
        return deg[a] > deg[b] || (deg[a] == deg[b] && a < b);
    });
    vector<int> color(n + 1, 0);
    for (int i : order) {
        vector<int> conf(4, 0);
        for (int nei : adj[i]) {
            int c = color[nei];
            if (c != 0) conf[c]++;
        }
        int best = 1;
        int minc = conf[1];
        for (int c = 2; c <= 3; c++) {
            if (conf[c] < minc) {
                minc = conf[c];
                best = c;
            }
        }
        color[i] = best;
    }
    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << " ";
        cout << color[i];
    }
    cout << endl;
    return 0;
}