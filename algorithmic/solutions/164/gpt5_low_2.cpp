#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<vector<int>> st(m);
    vector<pair<int,int>> pos(n+1); // pos[v] = {stack, index}
    int per = n / m;
    for (int i = 0; i < m; ++i) {
        st[i].resize(per);
        for (int j = 0; j < per; ++j) {
            int x; cin >> x;
            st[i][j] = x;
            pos[x] = {i, j};
        }
    }
    vector<pair<int,int>> ops;
    ops.reserve(2*n);
    
    for (int v = 1; v <= n; ++v) {
        auto [s, idx] = pos[v];
        int h = (int)st[s].size();
        if (idx != h - 1) {
            // choose destination stack t (not s) with minimal size
            int t = -1, bestSize = INT_MAX;
            for (int i = 0; i < m; ++i) if (i != s) {
                int sz = (int)st[i].size();
                if (sz < bestSize) {
                    bestSize = sz;
                    t = i;
                }
            }
            int w = st[s][idx + 1];
            // move segment [idx+1, h-1] to t
            for (int k = idx + 1; k < h; ++k) {
                int x = st[s][k];
                st[t].push_back(x);
                pos[x] = {t, (int)st[t].size() - 1};
            }
            st[s].resize(idx + 1);
            ops.emplace_back(w, t + 1);
        }
        // now v is at top of stack s
        st[s].pop_back();
        ops.emplace_back(v, 0);
        // pos[v] no longer needed
    }
    
    for (auto &p : ops) {
        cout << p.first << ' ' << p.second << '\n';
    }
    return 0;
}