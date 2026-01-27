#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if(!(cin >> T)) return 0;
    while (T--) {
        int n;
        cin >> n;
        vector<vector<int>> adj(n + 1);
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }

        vector<int> parent(n + 1, 0), depth(n + 1, 0), tin(n + 1, 0), tout(n + 1, 0), ord(n + 1, 0);
        int timer = 0;
        function<void(int,int)> dfs = [&](int u, int p) {
            parent[u] = p;
            depth[u] = (p == 0 ? 0 : depth[p] + 1);
            tin[u] = ++timer;
            ord[timer] = u;
            for (int v : adj[u]) if (v != p) {
                dfs(v, u);
            }
            tout[u] = timer;
        };
        dfs(1, 0);

        vector<char> inS(n + 1, 1);
        int qcount = 0;

        auto in_sub = [&](int v, int x) -> bool {
            return tin[v] >= tin[x] && tin[v] <= tout[x];
        };

        while (true) {
            int Ssize = 0;
            for (int i = 1; i <= n; ++i) if (inS[i]) ++Ssize;
            if (Ssize == 1) {
                int ansnode = 1;
                for (int i = 1; i <= n; ++i) if (inS[i]) { ansnode = i; break; }
                cout << "! " << ansnode << endl;
                cout.flush();
                break;
            }

            vector<int> bit(n + 1, 0);
            for (int i = 1; i <= n; ++i) if (inS[i]) bit[tin[i]] = 1;
            for (int i = 1; i <= n; ++i) bit[i] += bit[i - 1];

            auto count_in_sub = [&](int x) -> int {
                return bit[tout[x]] - bit[tin[x] - 1];
            };

            int best = 1;
            int best_worst = INT_MAX;
            for (int x = 1; x <= n; ++x) {
                int s_in = count_in_sub(x);
                int worst = max(s_in, Ssize - s_in);
                if (worst < best_worst || (worst == best_worst && depth[x] < depth[best])) {
                    best_worst = worst;
                    best = x;
                }
            }

            cout << "? " << best << endl;
            cout.flush();
            int resp;
            if(!(cin >> resp)) return 0;
            ++qcount;
            if (qcount > 160) return 0;

            vector<char> newInS(n + 1, 0);
            if (resp == 1) {
                for (int t = tin[best]; t <= tout[best]; ++t) {
                    int v = ord[t];
                    if (inS[v]) newInS[v] = 1;
                }
            } else {
                for (int v = 1; v <= n; ++v) if (inS[v]) {
                    if (!in_sub(v, best)) {
                        int u = (v == 1 ? 1 : parent[v]);
                        newInS[u] = 1;
                    }
                }
            }
            inS.swap(newInS);
        }
    }
    return 0;
}