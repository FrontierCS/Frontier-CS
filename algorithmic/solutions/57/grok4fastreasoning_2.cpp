#include <bits/stdc++.h>
using namespace std;

int main() {
    int t;
    cin >> t;
    for (int test = 0; test < t; test++) {
        int n;
        cin >> n;
        vector<vector<int>> adj(n + 1);
        for (int i = 0; i < n - 1; i++) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
        vector<int> f(n + 1, 0);
        long long sum_all = 0;
        for (int u = 1; u <= n; u++) {
            cout << "? 1 1 " << u << endl;
            cin >> f[u];
            sum_all += f[u];
        }
        vector<int> candidates;
        for (int i = 1; i <= n; i++) {
            if (abs(f[i]) == 1) candidates.push_back(i);
        }
        int nc = candidates.size();
        if (nc == 0) continue; // assume not happen
        vector<vector<int>> all_subs(nc, vector<int>(n + 1, 0));
        for (int i = 0; i < nc; i++) {
            int s = candidates[i];
            auto& temp_sub = all_subs[i];
            function<int(int, int)> dfs_size = [&](int u, int p) -> int {
                temp_sub[u] = 1;
                for (int v : adj[u]) {
                    if (v != p) {
                        temp_sub[u] += dfs_size(v, u);
                    }
                }
                return temp_sub[u];
            };
            dfs_size(s, -1);
        }
        vector<int> current(nc);
        iota(current.begin(), current.end(), 0);
        while (current.size() > 1) {
            int best_loc = -1;
            int min_maxf = n + 1;
            for (int loc : current) {
                vector<int> freq(n + 2, 0);
                int ss = candidates[loc];
                for (int cl : current) {
                    int szz = all_subs[cl][ss];
                    freq[szz]++;
                }
                int maxf = 0;
                for (int k = 1; k <= n; k++) maxf = max(maxf, freq[k]);
                if (maxf < min_maxf) {
                    min_maxf = maxf;
                    best_loc = loc;
                }
            }
            int s0 = candidates[best_loc];
            cout << "? 2 " << s0 << endl;
            cout << "? 1 " << n;
            for (int i = 1; i <= n; i++) cout << " " << i;
            cout << endl;
            long long sum_new;
            cin >> sum_new;
            long long delta = sum_new - sum_all;
            long long szz = -delta / 2;
            cout << "? 2 " << s0 << endl;
            vector<int> new_cur;
            for (int cl : current) {
                int this_sz = all_subs[cl][s0];
                if (this_sz == szz) new_cur.push_back(cl);
            }
            current = new_cur;
        }
        int final_i = (current.empty() ? 0 : current[0]);
        int root = candidates[final_i];
        vector<int> val(n + 1);
        function<void(int, int)> setv = [&](int u, int p) {
            if (p == -1) val[u] = f[u];
            else val[u] = f[u] - f[p];
            for (int v : adj[u]) {
                if (v != p) {
                    setv(v, u);
                }
            }
        };
        setv(root, -1);
        cout << "!";
        for (int i = 1; i <= n; i++) {
            cout << " " << val[i];
        }
        cout << endl;
    }
    return 0;
}