#include <bits/stdc++.h>
using namespace std;

struct Fenwick {
    int n;
    vector<int> bit;
    Fenwick(int n=0){ init(n); }
    void init(int n_) {
        n = n_;
        bit.assign(n + 1, 0);
    }
    void add(int idx, int val) { // idx: 0-based
        for (idx++; idx <= n; idx += idx & -idx) bit[idx] += val;
    }
    int sumPrefix(int idx) const { // idx: 0-based
        if (idx < 0) return 0;
        int res = 0;
        for (idx++; idx > 0; idx -= idx & -idx) res += bit[idx];
        return res;
    }
    int rangeSum(int l, int r) const { // inclusive, 0-based
        if (r < l) return 0;
        return sumPrefix(r) - sumPrefix(l - 1);
    }
};

static inline bool inSubtree(int u, int x, const vector<int>& tin, const vector<int>& tout) {
    return tin[u] >= tin[x] && tin[u] < tout[x];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    while (t--) {
        int n;
        cin >> n;
        vector<vector<int>> adj(n + 1);
        for (int i = 0; i < n - 1; i++) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }

        vector<int> parent(n + 1, 1), depth(n + 1, 0), tin(n + 1, 0), tout(n + 1, 0);
        int timer = 0;

        function<void(int,int)> dfs = [&](int v, int p) {
            parent[v] = p;
            depth[v] = (v == p ? 0 : depth[p] + 1);
            tin[v] = timer++;
            for (int to : adj[v]) if (to != p) dfs(to, v);
            tout[v] = timer;
        };
        dfs(1, 1);

        vector<int> S;
        S.reserve(n);
        for (int i = 1; i <= n; i++) S.push_back(i);

        Fenwick fw(n);
        vector<int> mark(n + 1, 0);
        int markIter = 1;
        int queries = 0;

        while ((int)S.size() > 1) {
            fw.init(n);
            for (int u : S) fw.add(tin[u], 1);

            int best = -1;
            int bestImb = INT_MAX, bestDepth = INT_MAX;
            int sz = (int)S.size();

            for (int u : S) {
                int cnt = fw.rangeSum(tin[u], tout[u] - 1);
                if (cnt <= 0 || cnt >= sz) continue;
                int imb = max(cnt, sz - cnt);
                if (imb < bestImb || (imb == bestImb && depth[u] < bestDepth)) {
                    bestImb = imb;
                    bestDepth = depth[u];
                    best = u;
                }
            }

            if (best == -1) best = S.back();

            cout << "? " << best << "\n";
            cout.flush();

            int ans;
            if (!(cin >> ans)) return 0;
            if (ans == -1) return 0;

            queries++;
            if (queries > 160) return 0;

            vector<int> newS;
            newS.reserve(S.size());

            if (ans == 1) {
                for (int u : S) {
                    if (inSubtree(u, best, tin, tout)) newS.push_back(u);
                }
            } else {
                if (++markIter == INT_MAX) {
                    fill(mark.begin(), mark.end(), 0);
                    markIter = 1;
                }
                for (int u : S) {
                    if (!inSubtree(u, best, tin, tout)) {
                        int v = (u == 1 ? 1 : parent[u]);
                        if (mark[v] != markIter) {
                            mark[v] = markIter;
                            newS.push_back(v);
                        }
                    }
                }
            }

            S.swap(newS);
        }

        int result = S[0];
        cout << "! " << result << "\n";
        cout.flush();
    }

    return 0;
}