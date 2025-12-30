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
        vector<long long> f(n + 1, 0);
        long long current_S = 0;
        for (int u = 1; u <= n; ++u) {
            cout << "? 1 1 " << u << endl;
            cout.flush();
            long long res;
            cin >> res;
            f[u] = res;
            current_S += res;
        }
        vector<int> cands;
        for (int r = 1; r <= n; ++r) {
            if (f[r] == 1 || f[r] == -1) {
                cands.push_back(r);
            }
        }
        int mm = cands.size();
        struct Hyp {
            int root;
            vector<int> val;
            vector<int> subsz;
        };
        vector<Hyp> hyps(mm);
        for (int idx = 0; idx < mm; ++idx) {
            int r = cands[idx];
            vector<int> par(n + 1, -1);
            vector<bool> visited(n + 1, false);
            queue<int> qq;
            qq.push(r);
            visited[r] = true;
            par[r] = -2;
            while (!qq.empty()) {
                int uu = qq.front();
                qq.pop();
                for (int nei : adj[uu]) {
                    if (!visited[nei]) {
                        visited[nei] = true;
                        par[nei] = uu;
                        qq.push(nei);
                    }
                }
            }
            vector<int> tval(n + 1);
            tval[r] = (int)f[r];
            for (int uu = 1; uu <= n; ++uu) {
                if (uu == r) continue;
                int pp = par[uu];
                tval[uu] = (int)(f[uu] - f[pp]);
            }
            vector<int> tsub(n + 1, 0);
            function<int(int)> dfs = [&](int uu) -> int {
                int ssz = 1;
                for (int nei : adj[uu]) {
                    if (par[nei] == uu) {
                        ssz += dfs(nei);
                    }
                }
                tsub[uu] = ssz;
                return ssz;
            };
            dfs(r);
            hyps[idx] = {r, tval, tsub};
        }
        vector<bool> is_active(mm, true);
        int num_act = mm;
        long long cur_S = current_S;
        while (num_act > 1) {
            int ch_v = -1;
            bool found = false;
            for (int vv = 1; vv <= n; ++vv) {
                set<long long> pred_ns;
                for (int i = 0; i < mm; ++i) {
                    if (!is_active[i]) continue;
                    long long vval = hyps[i].val[vv];
                    long long ss = hyps[i].subsz[vv];
                    long long del = -2LL * vval * ss;
                    long long pns = cur_S + del;
                    pred_ns.insert(pns);
                }
                if (pred_ns.size() > 1) {
                    ch_v = vv;
                    found = true;
                    break;
                }
            }
            if (!found) {
                break;
            }
            cout << "? 2 " << ch_v << endl;
            cout.flush();
            cout << "? 1 " << n;
            for (int i = 1; i <= n; ++i) {
                cout << " " << i;
            }
            cout << endl;
            cout.flush();
            long long new_s;
            cin >> new_s;
            vector<bool> new_active(mm, false);
            int new_num = 0;
            for (int i = 0; i < mm; ++i) {
                if (!is_active[i]) continue;
                long long vval = hyps[i].val[ch_v];
                long long ss = hyps[i].subsz[ch_v];
                long long del = -2LL * vval * ss;
                long long pns = cur_S + del;
                if (pns == new_s) {
                    new_active[i] = true;
                    ++new_num;
                }
            }
            for (int i = 0; i < mm; ++i) {
                if (new_active[i]) {
                    hyps[i].val[ch_v] = -hyps[i].val[ch_v];
                }
            }
            is_active = new_active;
            num_act = new_num;
            cur_S = new_s;
        }
        int the_hyp = -1;
        for (int i = 0; i < mm; ++i) {
            if (is_active[i]) {
                the_hyp = i;
                break;
            }
        }
        cout << "!";
        for (int j = 1; j <= n; ++j) {
            cout << " " << hyps[the_hyp].val[j];
        }
        cout << endl;
        cout.flush();
    }
    return 0;
}