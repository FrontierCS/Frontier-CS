#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    int h0 = n / m;

    vector<vector<int>> st(m);
    vector<int> stOf(n + 1, -1), idxIn(n + 1, -1);
    vector<char> removed(n + 1, 0);

    for (int i = 0; i < m; i++) {
        st[i].resize(h0);
        for (int j = 0; j < h0; j++) {
            cin >> st[i][j];
            stOf[st[i][j]] = i;
            idxIn[st[i][j]] = j;
        }
    }

    vector<pair<int,int>> ops;
    ops.reserve(5000);

    auto do_move = [&](int box, int dest) {
        int s = stOf[box];
        int j = idxIn[box];
        if (s < 0 || dest < 0 || dest >= m) return;

        // extract segment [j..end)
        int oldDestSize = (int)st[dest].size();
        vector<int> seg;
        seg.reserve((int)st[s].size() - j);
        for (int t = j; t < (int)st[s].size(); t++) seg.push_back(st[s][t]);
        st[s].resize(j);
        for (int t = 0; t < (int)seg.size(); t++) {
            int x = seg[t];
            stOf[x] = dest;
            idxIn[x] = oldDestSize + t;
        }
        st[dest].insert(st[dest].end(), seg.begin(), seg.end());

        ops.push_back({box, dest + 1}); // 1-indexed stack for output
    };

    auto do_remove = [&](int v) {
        int s = stOf[v];
        if (s < 0) return;
        if (st[s].empty() || st[s].back() != v) return;
        st[s].pop_back();
        removed[v] = 1;
        stOf[v] = -1;
        idxIn[v] = -1;
        ops.push_back({v, 0});
    };

    auto choose_dest = [&](int src) -> int {
        int best = -1;
        int bestH = INT_MAX;
        for (int i = 0; i < m; i++) {
            if (i == src) continue;
            int h = (int)st[i].size();
            if (h < bestH) {
                bestH = h;
                best = i;
            }
        }
        if (best == -1) best = (src + 1) % m;
        return best;
    };

    for (int v = 1; v <= n; v++) {
        int s = stOf[v];
        if (s < 0) continue;

        int p = idxIn[v];
        if (p != (int)st[s].size() - 1) {
            int aboveBox = st[s][p + 1];
            int dest = choose_dest(s);
            do_move(aboveBox, dest);
        }
        do_remove(v);
    }

    if ((int)ops.size() > 5000) ops.resize(5000);
    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }
    return 0;
}