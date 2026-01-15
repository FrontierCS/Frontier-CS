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
    vector<int> st;
    st.push_back(1);
    parent[1] = 0;

    // Iterative DFS to get traversal order and parents
    while (!st.empty()) {
        int v = st.back();
        st.pop_back();
        order.push_back(v);
        for (int to : g[v]) {
            if (to == parent[v]) continue;
            parent[to] = v;
            st.push_back(to);
        }
    }

    vector<int> sz(n + 1, 1);
    int centroid = 1;
    int best = n + 1;

    // Process in reverse order to compute subtree sizes and find centroid
    for (int i = n - 1; i >= 0; --i) {
        int v = order[i];
        int maxPart = n - sz[v];
        for (int to : g[v]) {
            if (to == parent[v]) continue;
            sz[v] += sz[to];
            maxPart = max(maxPart, sz[to]);
        }
        if (maxPart < best || (maxPart == best && v < centroid)) {
            best = maxPart;
            centroid = v;
        }
    }

    cout << centroid << '\n';
    return 0;
}