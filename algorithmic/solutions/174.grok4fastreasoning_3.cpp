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
    vector<int> color(n + 1, 0);
    vector<pair<int, int>> deg_id(n);
    for (int i = 1; i <= n; i++) {
        deg_id[i - 1] = {-(int)adj[i].size(), i};
    }
    sort(deg_id.begin(), deg_id.end());
    for (auto& p : deg_id) {
        int u = p.second;
        vector<int> cnt(4, 0);
        for (int v : adj[u]) {
            if (color[v] != 0) {
                cnt[color[v]]++;
            }
        }
        int best_c = 1;
        int min_conf = cnt[1];
        for (int c = 2; c <= 3; c++) {
            if (cnt[c] < min_conf) {
                min_conf = cnt[c];
                best_c = c;
            }
        }
        color[u] = best_c;
    }
    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << " ";
        cout << color[i];
    }
    cout << endl;
    return 0;
}