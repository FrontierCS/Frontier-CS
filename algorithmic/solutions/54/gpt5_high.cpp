#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    vector<vector<int>> g(n + 1);
    int edges_read = 0;
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        if (!(cin >> u >> v)) break;
        if (u >= 1 && u <= n && v >= 1 && v <= n) {
            g[u].push_back(v);
            g[v].push_back(u);
            ++edges_read;
        }
    }

    if (edges_read != n - 1) {
        // Fallback if edges are not provided properly
        cout << 1 << "\n";
        return 0;
    }

    vector<int> parent(n + 1, -2), order;
    order.reserve(n);
    stack<int> st;
    st.push(1);
    parent[1] = -1;
    while (!st.empty()) {
        int u = st.top(); st.pop();
        order.push_back(u);
        for (int v : g[u]) {
            if (parent[v] == -2) {
                parent[v] = u;
                st.push(v);
            }
        }
    }

    vector<int> sz(n + 1, 1);
    int centroid = 1;
    int best = n + 1;

    for (int i = (int)order.size() - 1; i >= 0; --i) {
        int u = order[i];
        int mx = n - sz[u];
        for (int v : g[u]) {
            if (parent[v] == u) {
                mx = max(mx, sz[v]);
            }
        }
        if (mx < best) {
            best = mx;
            centroid = u;
        }
        if (parent[u] != -1) {
            sz[parent[u]] += sz[u];
        }
    }

    cout << centroid << "\n";
    return 0;
}