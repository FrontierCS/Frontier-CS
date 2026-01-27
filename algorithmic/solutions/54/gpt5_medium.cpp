#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<long long> in;
    long long x;
    while (cin >> x) in.push_back(x);
    if (in.empty()) return 0;

    int idx = 0;
    int n = (int)in[idx++];

    // Attempt to read edges if provided: expect 2*(n-1) integers for edges
    int remaining = (int)in.size() - idx;
    int m = remaining / 2;
    if (m < n - 1) {
        // Not enough data to build a tree; fallback
        cout << 1 << "\n";
        return 0;
    }
    m = n - 1; // only use first n-1 edges if more provided

    vector<vector<int>> g(n + 1);
    for (int i = 0; i < m; ++i) {
        int u = (int)in[idx++];
        int v = (int)in[idx++];
        if (u >= 1 && u <= n && v >= 1 && v <= n) {
            g[u].push_back(v);
            g[v].push_back(u);
        }
    }

    // Handle trivial case
    if (n == 1) {
        cout << 1 << "\n";
        return 0;
    }

    // Iterative DFS to compute subtree sizes and max component sizes
    vector<int> parent(n + 1, 0), order;
    order.reserve(n);
    vector<int> stk;
    stk.reserve(n);
    stk.push_back(1);
    parent[1] = -1;

    while (!stk.empty()) {
        int u = stk.back();
        stk.pop_back();
        order.push_back(u);
        for (int v : g[u]) {
            if (v == parent[u]) continue;
            parent[v] = u;
            stk.push_back(v);
        }
    }

    vector<int> sz(n + 1, 0);
    vector<int> maxComp(n + 1, 0);
    for (int i = n - 1; i >= 0; --i) {
        int u = order[i];
        sz[u] = 1;
        int maxChild = 0;
        for (int v : g[u]) {
            if (v == parent[u]) continue;
            sz[u] += sz[v];
            if (sz[v] > maxChild) maxChild = sz[v];
        }
        maxComp[u] = max(maxChild, n - sz[u]);
    }

    int centroid = 1;
    for (int u = 2; u <= n; ++u) {
        if (maxComp[u] < maxComp[centroid]) centroid = u;
    }

    cout << centroid << "\n";
    return 0;
}