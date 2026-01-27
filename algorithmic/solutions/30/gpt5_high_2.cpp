#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        vector<vector<int>> adj(n + 1);
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }

        vector<int> parent(n + 1, 0), depth(n + 1, 0), tin(n + 1, 0), tout(n + 1, 0), order(n + 1, 0);
        int timer = 0;
        function<void(int,int)> dfs = [&](int u, int p) {
            parent[u] = p;
            tin[u] = ++timer;
            order[timer] = u;
            for (int v : adj[u]) if (v != p) {
                depth[v] = depth[u] + 1;
                dfs(v, u);
            }
            tout[u] = timer;
        };
        dfs(1, 0);

        vector<char> inS(n + 1, 1);
        vector<int> Slist;
        Slist.reserve(n);
        for (int i = 1; i <= n; ++i) Slist.push_back(i);

        vector<int> pref(n + 1, 0);
        auto rebuild_pref = [&]() {
            pref[0] = 0;
            for (int i = 1; i <= n; ++i) {
                pref[i] = pref[i - 1] + inS[order[i]];
            }
        };
        rebuild_pref();

        auto insideCount = [&](int x) -> int {
            return pref[tout[x]] - pref[tin[x] - 1];
        };

        auto inSub = [&](int v, int x) -> bool {
            return tin[v] >= tin[x] && tin[v] <= tout[x];
        };

        while ((int)Slist.size() > 1) {
            int m = (int)Slist.size();
            int bestX = 1;
            int bestMax = n + 5;

            for (int x = 1; x <= n; ++x) {
                int inside = insideCount(x);
                int outside = m - inside;
                int curMax = max(inside, outside);
                if (curMax < bestMax) {
                    bestMax = curMax;
                    bestX = x;
                }
            }

            cout << "? " << bestX << endl;
            cout.flush();

            int ans;
            if (!(cin >> ans)) return 0;
            if (ans == -1) return 0;

            if (ans == 1) {
                for (int v : Slist) {
                    if (!inSub(v, bestX)) inS[v] = 0;
                }
                vector<int> newS;
                newS.reserve(bestMax);
                for (int v : Slist) if (inS[v]) newS.push_back(v);
                Slist.swap(newS);
            } else {
                vector<char> newInS(n + 1, 0);
                vector<int> newS;
                newS.reserve(bestMax);
                for (int v : Slist) {
                    if (!inSub(v, bestX)) {
                        int u = (v == 1 ? 1 : parent[v]);
                        if (!newInS[u]) {
                            newInS[u] = 1;
                            newS.push_back(u);
                        }
                    }
                }
                inS.swap(newInS);
                Slist.swap(newS);
            }
            rebuild_pref();
        }

        int ansNode = Slist.empty() ? 1 : Slist.front();
        cout << "! " << ansNode << endl;
        cout.flush();
    }

    return 0;
}