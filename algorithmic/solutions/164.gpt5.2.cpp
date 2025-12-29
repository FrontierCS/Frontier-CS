#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    vector<vector<int>> st(m);
    int h = n / m;
    for (int i = 0; i < m; i++) {
        st[i].resize(h);
        for (int j = 0; j < h; j++) cin >> st[i][j];
    }

    vector<pair<int,int>> ops;
    const int INF = 1e9;

    auto find_box = [&](int v) -> pair<int,int> {
        for (int i = 0; i < m; i++) {
            for (int j = 0; j < (int)st[i].size(); j++) {
                if (st[i][j] == v) return {i, j};
            }
        }
        return {-1, -1};
    };

    auto min_in_stack = [&](int i) -> int {
        if (st[i].empty()) return INF;
        int mn = INF;
        for (int x : st[i]) mn = min(mn, x);
        return mn;
    };

    for (int v = 1; v <= n; v++) {
        auto [s, idx] = find_box(v);
        if (s < 0) return 0;

        if (idx != (int)st[s].size() - 1) {
            int start = idx + 1;
            int moveBox = st[s][start];

            int best = -1;
            int bestMin = -1;
            int bestHeight = INF;

            for (int i = 0; i < m; i++) if (i != s) {
                int mn = min_in_stack(i); // empty -> INF
                int ht = (int)st[i].size();
                if (mn > bestMin || (mn == bestMin && ht < bestHeight)) {
                    bestMin = mn;
                    bestHeight = ht;
                    best = i;
                }
            }
            if (best < 0) best = (s + 1) % m;

            vector<int> seg(st[s].begin() + start, st[s].end());
            st[s].resize(start);
            st[best].insert(st[best].end(), seg.begin(), seg.end());

            ops.push_back({moveBox, best + 1});
        }

        if (st[s].empty() || st[s].back() != v) return 0;
        st[s].pop_back();
        ops.push_back({v, 0});
    }

    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }
    return 0;
}