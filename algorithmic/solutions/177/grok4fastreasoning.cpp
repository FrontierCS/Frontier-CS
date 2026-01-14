#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int n, m;
    cin >> n >> m;
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    vector<int> deg(n + 1);
    for (int i = 1; i <= n; i++) {
        deg[i] = adj[i].size();
    }
    vector<pair<int, int>> nodes;
    for (int i = 1; i <= n; i++) {
        nodes.emplace_back(-deg[i], i);
    }
    sort(nodes.begin(), nodes.end());
    vector<int> color(n + 1, 0);
    for (auto& p : nodes) {
        int v = p.second;
        vector<int> conf(4, 0);
        for (int u : adj[v]) {
            if (color[u]) {
                conf[color[u]]++;
            }
        }
        int min_conf = INT_MAX;
        int best_c = 0;
        for (int c = 1; c <= 3; c++) {
            int cc = conf[c];
            if (cc < min_conf || (cc == min_conf && c < best_c)) {
                min_conf = cc;
                best_c = c;
            }
        }
        color[v] = best_c;
    }
    for (int i = 1; i <= n; i++) {
        cout << color[i] << (i < n ? " " : "\n");
    }
    return 0;
}