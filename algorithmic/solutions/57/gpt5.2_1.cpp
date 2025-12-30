#include <bits/stdc++.h>
using namespace std;

static inline void flush_out() { cout.flush(); }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        vector<vector<int>> adj(n + 1);
        vector<int> deg(n + 1, 0);
        for (int i = 0; i < n - 1; i++) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
            deg[u]++; deg[v]++;
        }

        int leaf = 1;
        for (int i = 1; i <= n; i++) {
            if (deg[i] == 1) { leaf = i; break; }
        }

        vector<int> order;
        order.reserve(n);
        order.push_back(leaf);
        for (int i = 1; i <= n; i++) if (i != leaf) order.push_back(i);

        string allNodes;
        allNodes.reserve(5 * n);
        for (int i = 1; i <= n; i++) {
            allNodes.push_back(' ');
            allNodes += to_string(i);
        }

        auto toggle = [&](int u) {
            cout << "? 2 " << u << '\n';
            flush_out();
        };

        auto querySumAll = [&]() -> long long {
            cout << "? 1 " << n << allNodes << '\n';
            flush_out();
            long long ans;
            if (!(cin >> ans)) exit(0);
            return ans;
        };

        vector<long long> S(n + 1, 0); // S[i] after toggling order[i-1]
        vector<int> sub(n + 1, -1);
        vector<int> orig(n + 1, 0);

        for (int i = 1; i <= n; i++) {
            toggle(order[i - 1]);
            S[i] = querySumAll();
            if (i >= 2) {
                long long delta = S[i] - S[i - 1];
                int u = order[i - 1];
                sub[u] = (int)(llabs(delta) / 2);
                orig[u] = (delta < 0 ? 1 : -1); // delta = -2 * orig[u] * sub[u]
            }
        }

        int root = -1;
        for (int i = 2; i <= n; i++) {
            int u = order[i - 1];
            if (sub[u] == n) { root = u; break; }
        }
        if (root == -1) root = leaf;

        sub[leaf] = (root == leaf ? n : 1);

        vector<int> parent(n + 1, 0);
        vector<vector<int>> children(n + 1);
        parent[root] = 0;
        vector<int> st;
        st.reserve(n);
        st.push_back(root);
        while (!st.empty()) {
            int u = st.back();
            st.pop_back();
            for (int v : adj[u]) {
                if (v == parent[u]) continue;
                if (sub[v] < sub[u]) {
                    parent[v] = u;
                    children[u].push_back(v);
                    st.push_back(v);
                }
            }
        }

        auto computeSumState = [&](int leafValState) -> long long {
            vector<long long> f(n + 1, 0);
            auto getVal = [&](int u) -> int {
                if (u == leaf) return leafValState;
                return orig[u];
            };
            long long sum = 0;
            vector<int> stk;
            stk.reserve(n);
            stk.push_back(root);
            f[root] = getVal(root);
            sum += f[root];
            while (!stk.empty()) {
                int u = stk.back();
                stk.pop_back();
                for (int v : children[u]) {
                    f[v] = f[u] + getVal(v);
                    sum += f[v];
                    stk.push_back(v);
                }
            }
            return sum;
        };

        // Determine orig[leaf] by matching S[1] (state after first toggle: leaf flipped)
        // If origLeaf = +1 => leafValState = -1; if origLeaf = -1 => leafValState = +1.
        long long targetS1 = S[1];
        bool okPos = (computeSumState(-1) == targetS1); // corresponds to orig[leaf] = +1
        if (okPos) orig[leaf] = 1;
        else orig[leaf] = -1;

        cout << "!";
        for (int i = 1; i <= n; i++) {
            cout << ' ' << -orig[i];
        }
        cout << '\n';
        flush_out();
    }

    return 0;
}