#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    cin >> t;
    for (int test = 0; test < t; ++test) {
        int n;
        cin >> n;
        vector<vector<int>> adj(n + 1);
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
        vector<int> parent(n + 1, 0);
        vector<int> depth(n + 1, 0);
        vector<int> in_time(n + 1, 0);
        vector<int> out_time(n + 1, 0);
        vector<vector<int>> child(n + 1);
        int timer = 0;
        function<void(int, int)> dfs = [&](int u, int p) {
            parent[u] = p;
            depth[u] = (p == 0 ? 0 : depth[p] + 1);
            in_time[u] = timer++;
            for (int v : adj[u]) {
                if (v != p) {
                    child[u].push_back(v);
                    dfs(v, u);
                }
            }
            out_time[u] = timer;
        };
        dfs(1, 0);
        set<int> S;
        for (int i = 1; i <= n; ++i) S.insert(i);
        int queries = 0;
        while (S.size() > 1) {
            vector<bool> is_pos(n + 1, false);
            for (int p : S) is_pos[p] = true;
            vector<int> sub_count(n + 1, 0);
            function<void(int)> compute_count = [&](int u) {
                sub_count[u] = is_pos[u] ? 1 : 0;
                for (int v : child[u]) {
                    compute_count(v);
                    sub_count[u] += sub_count[v];
                }
            };
            compute_count(1);
            int total = S.size();
            int target = total / 2;
            int min_diff = INT_MAX;
            int min_d = INT_MAX;
            int best_x = 1;
            for (int u = 1; u <= n; ++u) {
                int c = sub_count[u];
                int diff = abs(c - target);
                int d = depth[u];
                if (c > 0 && (diff < min_diff || (diff == min_diff && d < min_d))) {
                    min_diff = diff;
                    min_d = d;
                    best_x = u;
                }
            }
            cout << "? " << best_x << endl;
            cout.flush();
            int resp;
            cin >> resp;
            ++queries;
            set<int> newS;
            for (int p : S) {
                bool in_sub = (in_time[p] >= in_time[best_x] && in_time[p] < out_time[best_x]);
                int r = in_sub ? 1 : 0;
                if (r == resp) {
                    int np = (resp == 0 && p != 1) ? parent[p] : p;
                    newS.insert(np);
                }
            }
            S = move(newS);
        }
        int ans = *S.begin();
        cout << "! " << ans << endl;
        cout.flush();
    }
    return 0;
}