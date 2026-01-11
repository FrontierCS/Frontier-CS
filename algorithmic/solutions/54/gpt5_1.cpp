#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    bool first_output = true;
    while (cin >> n) {
        vector<vector<int>> g(n + 1);
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            if (!(cin >> u >> v)) return 0;
            g[u].push_back(v);
            g[v].push_back(u);
        }

        vector<int> parent(n + 1, -1);
        vector<int> order;
        order.reserve(n);
        vector<int> st;
        st.push_back(1);
        parent[1] = 0;
        while (!st.empty()) {
            int u = st.back(); st.pop_back();
            order.push_back(u);
            for (int v : g[u]) {
                if (v == parent[u]) continue;
                parent[v] = u;
                st.push_back(v);
            }
        }

        vector<int> sub(n + 1, 1);
        int best = 1;
        int bestMax = n;
        for (int i = (int)order.size() - 1; i >= 0; --i) {
            int u = order[i];
            int maxChild = 0;
            for (int v : g[u]) {
                if (v == parent[u]) continue;
                sub[u] += sub[v];
                if (sub[v] > maxChild) maxChild = sub[v];
            }
            int rest = n - sub[u];
            int maxi = max(maxChild, rest);
            if (maxi < bestMax || (maxi == bestMax && u < best)) {
                bestMax = maxi;
                best = u;
            }
        }

        cout << best << '\n';
    }
    return 0;
}