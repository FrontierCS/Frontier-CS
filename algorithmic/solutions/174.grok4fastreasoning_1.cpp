#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    vector<pair<int, int>> degs;
    for (int i = 1; i <= n; i++) {
        degs.push_back({-(int)adj[i].size(), i});
    }
    sort(degs.begin(), degs.end());
    vector<int> color(n + 1, 0);
    for (auto& p : degs) {
        int v = p.second;
        vector<int> cnt(4, 0);
        for (int u : adj[v]) {
            if (color[u]) cnt[color[u]]++;
        }
        int best = 1;
        int minc = cnt[1];
        for (int c = 2; c <= 3; c++) {
            if (cnt[c] < minc) {
                minc = cnt[c];
                best = c;
            }
        }
        color[v] = best;
    }
    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << " ";
        cout << color[i];
    }
    cout << endl;
    return 0;
}