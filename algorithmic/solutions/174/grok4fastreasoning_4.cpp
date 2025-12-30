#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n, m;
    cin >> n >> m;
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    vector<pair<int, int>> order(n);
    for (int i = 1; i <= n; i++) {
        order[i - 1] = {-(int)adj[i].size(), i};
    }
    sort(order.begin(), order.end());
    vector<int> color(n + 1, 0);
    for (auto& p : order) {
        int u = p.second;
        vector<int> cnt(4, 0);
        for (int v : adj[u]) {
            int c = color[v];
            if (c != 0) cnt[c]++;
        }
        int min_conf = INT_MAX;
        int best_col = -1;
        for (int c = 1; c <= 3; c++) {
            if (cnt[c] < min_conf) {
                min_conf = cnt[c];
                best_col = c;
            }
        }
        color[u] = best_col;
    }
    for (int i = 1; i <= n; i++) {
        cout << color[i];
        if (i < n) cout << " ";
        else cout << "\n";
    }
    return 0;
}