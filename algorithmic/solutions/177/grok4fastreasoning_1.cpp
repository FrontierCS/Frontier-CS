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
    vector<pair<int, int>> verts;
    for (int i = 1; i <= n; i++) {
        verts.push_back({-static_cast<int>(adj[i].size()), i});
    }
    sort(verts.begin(), verts.end());
    vector<int> color(n + 1, 0);
    for (auto& p : verts) {
        int i = p.second;
        vector<int> cnt(4, 0);
        for (int nei : adj[i]) {
            if (color[nei] != 0) {
                cnt[color[nei]]++;
            }
        }
        int best = 1;
        for (int c = 2; c <= 3; c++) {
            if (cnt[c] < cnt[best]) {
                best = c;
            }
        }
        color[i] = best;
    }
    for (int i = 1; i <= n; i++) {
        cout << color[i];
        if (i < n) cout << ' ';
        else cout << '\n';
    }
    return 0;
}