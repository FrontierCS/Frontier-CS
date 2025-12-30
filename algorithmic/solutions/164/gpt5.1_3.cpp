#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<vector<int>> st(m);
    int h = n / m;
    for (int i = 0; i < m; ++i) {
        st[i].resize(h);
        for (int j = 0; j < h; ++j) cin >> st[i][j];
    }

    vector<pair<int,int>> ops;

    for (int v = 1; v <= n; ++v) {
        int src = -1, pos = -1;
        // Find box v
        for (int i = 0; i < m && src == -1; ++i) {
            for (int j = 0; j < (int)st[i].size(); ++j) {
                if (st[i][j] == v) {
                    src = i;
                    pos = j;
                    break;
                }
            }
        }
        if (src == -1) continue; // should not happen

        int sz = (int)st[src].size();
        if (pos != sz - 1) {
            int posAbove = pos + 1;
            int wVal = st[src][posAbove]; // bottom of chunk
            int dest = (src + 1) % m;
            // Operation 1: move chunk starting at wVal to dest
            ops.emplace_back(wVal, dest + 1);
            vector<int> chunk;
            chunk.reserve(sz - posAbove);
            for (int i = posAbove; i < sz; ++i) chunk.push_back(st[src][i]);
            st[src].resize(posAbove);
            for (int x : chunk) st[dest].push_back(x);
        }
        // Now v is at top of stack src
        ops.emplace_back(v, 0);
        st[src].pop_back();
    }

    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }

    return 0;
}