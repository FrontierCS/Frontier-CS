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
    vector<int> degree(n + 1, 0);
    for (int i = 1; i <= n; i++) {
        degree[i] = adj[i].size();
    }
    vector<int> order(n);
    iota(order.begin(), order.end(), 1);
    sort(order.begin(), order.end(), [&](int a, int b) {
        return degree[a] > degree[b];
    });
    vector<int> color(n + 1, 0);
    for (int idx : order) {
        vector<int> conflict(4, 0);
        for (int nei : adj[idx]) {
            if (color[nei] != 0) {
                conflict[color[nei]]++;
            }
        }
        int best = 1;
        int min_conf = conflict[1];
        for (int c = 2; c <= 3; c++) {
            if (conflict[c] < min_conf) {
                min_conf = conflict[c];
                best = c;
            }
        }
        color[idx] = best;
    }
    for (int i = 1; i <= n; i++) {
        cout << color[i];
        if (i < n) cout << " ";
        else cout << "\n";
    }
    return 0;
}