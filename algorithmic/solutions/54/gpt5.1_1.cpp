#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<vector<int>> g(n + 1);
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        g[u].push_back(v);
        g[v].push_back(u);
    }

    vector<int> parent(n + 1, 0), order;
    order.reserve(n);
    queue<int> q;
    q.push(1);
    parent[1] = -1;

    while (!q.empty()) {
        int u = q.front(); q.pop();
        order.push_back(u);
        for (int v : g[u]) {
            if (v == parent[u]) continue;
            parent[v] = u;
            q.push(v);
        }
    }

    vector<int> sub(n + 1, 0);
    int centroid = 1;
    int best = n;

    for (int i = n - 1; i >= 0; --i) {
        int u = order[i];
        sub[u] = 1;
        int max_part = 0;
        for (int v : g[u]) {
            if (v == parent[u]) continue;
            sub[u] += sub[v];
            max_part = max(max_part, sub[v]);
        }
        int up_part = n - sub[u];
        max_part = max(max_part, up_part);
        if (max_part < best) {
            best = max_part;
            centroid = u;
        }
    }

    cout << centroid << '\n';
    return 0;
}