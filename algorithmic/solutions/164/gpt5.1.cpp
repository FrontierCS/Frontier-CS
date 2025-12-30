#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<vector<int>> st(m);
    int per = n / max(1, m);
    for (int i = 0; i < m; ++i) {
        st[i].resize(per);
        for (int j = 0; j < per; ++j) {
            cin >> st[i][j];
        }
    }

    // pos[v] = (stack index, position from bottom)
    vector<pair<int,int>> pos(n + 1);
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < (int)st[i].size(); ++j) {
            int v = st[i][j];
            pos[v] = {i, j};
        }
    }

    vector<pair<int,int>> ops;

    for (int v = 1; v <= n; ++v) {
        auto [s, idx] = pos[v];
        int h = (int)st[s].size();

        if (idx != h - 1) {
            int above_idx = idx + 1;
            int x = st[s][above_idx];
            int t = (s + 1) % m;  // destination stack (different from s since m >= 2)

            int start = above_idx;
            int h2 = (int)st[s].size();
            vector<int> tmp;
            tmp.reserve(h2 - start);
            for (int i = start; i < h2; ++i) tmp.push_back(st[s][i]);
            st[s].resize(start);

            for (int w : tmp) {
                pos[w] = {t, (int)st[t].size()};
                st[t].push_back(w);
            }

            ops.emplace_back(x, t + 1);  // operation 1
        }

        ops.emplace_back(v, 0);  // operation 2
        st[s].pop_back();
        // pos[v] no longer needed
    }

    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }

    return 0;
}