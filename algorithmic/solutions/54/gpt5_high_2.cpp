#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    while ( (cin >> n) ) {
        vector<vector<int>> g(n + 1);
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            g[u].push_back(v);
            g[v].push_back(u);
        }

        vector<int> parent(n + 1, -1);
        vector<int> order;
        order.reserve(n);
        stack<int> st;
        st.push(1);
        parent[1] = 0;

        while (!st.empty()) {
            int u = st.top(); st.pop();
            order.push_back(u);
            for (int v : g[u]) {
                if (v == parent[u]) continue;
                parent[v] = u;
                st.push(v);
            }
        }

        vector<int> sz(n + 1, 1);
        vector<int> maxchild(n + 1, 0);
        for (int i = (int)order.size() - 1; i >= 0; --i) {
            int u = order[i];
            for (int v : g[u]) {
                if (v == parent[u]) continue;
                sz[u] += sz[v];
                maxchild[u] = max(maxchild[u], sz[v]);
            }
        }

        int best = 1, bestVal = n;
        for (int u = 1; u <= n; ++u) {
            int val = max(maxchild[u], n - sz[u]);
            if (val < bestVal || (val == bestVal && u < best)) {
                bestVal = val;
                best = u;
            }
        }
        cout << best << "\n";
    }

    return 0;
}