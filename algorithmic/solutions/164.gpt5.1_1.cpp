#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;
    int h0 = n / m;

    vector<vector<int>> st(m + 1);
    for (int i = 1; i <= m; ++i) {
        st[i].reserve(n);
        for (int j = 0; j < h0; ++j) {
            int x;
            cin >> x;
            st[i].push_back(x);
        }
    }

    vector<pair<int,int>> ops;
    ops.reserve(2 * n);

    for (int v = 1; v <= n; ++v) {
        int s = -1, pos = -1;
        for (int i = 1; i <= m && s == -1; ++i) {
            for (int j = 0; j < (int)st[i].size(); ++j) {
                if (st[i][j] == v) {
                    s = i;
                    pos = j;
                    break;
                }
            }
        }
        if (s == -1) continue; // should not happen

        int h = (int)st[s].size();
        if (pos != h - 1) {
            int u = st[s][pos + 1];
            int t = s % m + 1; // destination stack different from s

            vector<int> seg;
            seg.reserve(h - pos - 1);
            for (int k = pos + 1; k < h; ++k) {
                seg.push_back(st[s][k]);
            }
            st[s].resize(pos + 1);
            for (int x : seg) st[t].push_back(x);

            ops.push_back({u, t});
        }

        // Remove v from top
        if (!st[s].empty() && st[s].back() == v) {
            st[s].pop_back();
        } else {
            // Fallback search (should rarely happen)
            bool found = false;
            for (int i = 1; i <= m && !found; ++i) {
                if (!st[i].empty() && st[i].back() == v) {
                    st[i].pop_back();
                    s = i;
                    found = true;
                }
            }
        }
        ops.push_back({v, 0});
    }

    for (auto &p : ops) {
        cout << p.first << ' ' << p.second << '\n';
    }

    return 0;
}