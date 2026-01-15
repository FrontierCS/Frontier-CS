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
    st.reserve(n);
    st.push_back(1);
    parent[1] = 0;

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

    vector<int> subtree(n + 1, 0);
    int centroid = 1;
    int best = n;

    for (int i = n - 1; i >= 0; --i) {
        int v = order[i];
        subtree[v] = 1;
        int mx = 0;
        for (int to : g[v]) {
            if (to == parent[v]) continue;
            subtree[v] += subtree[to];
            mx = max(mx, subtree[to]);
        }
        int up = n - subtree[v];
        mx = max(mx, up);
        if (mx < best) {
            best = mx;
            centroid = v;
        }
    }

    cout << centroid << '\n';
    return 0;
}