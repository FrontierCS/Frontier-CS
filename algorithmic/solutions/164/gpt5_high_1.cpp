#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    int h = n / m;

    vector<vector<int>> st(m);
    vector<pair<int,int>> pos(n+1, {-1,-1}); // pos[v] = {stack index, position index}
    for (int i = 0; i < m; ++i) {
        st[i].resize(h);
        for (int j = 0; j < h; ++j) {
            int x; cin >> x;
            st[i][j] = x;
            pos[x] = {i, j}; // j: 0-based from bottom to top
        }
    }

    vector<pair<int,int>> ops;

    auto chooseDest = [&](int s) -> int {
        int best = -1;
        size_t bestSize = numeric_limits<size_t>::max();
        // Prefer empty stack
        for (int t = 0; t < m; ++t) {
            if (t == s) continue;
            if (st[t].empty()) return t;
        }
        // Otherwise choose minimal size
        for (int t = 0; t < m; ++t) {
            if (t == s) continue;
            if (st[t].size() < bestSize) {
                bestSize = st[t].size();
                best = t;
            }
        }
        if (best == -1) {
            // Fallback (should not happen with m>=2)
            best = (s + 1) % m;
            if (best == s) best = (best + 1) % m;
        }
        return best;
    };

    auto move_by_box = [&](int boxValue, int dest) {
        auto [s, idx] = pos[boxValue];
        if (s == dest) return; // avoid no-op; but should not happen
        vector<int> seg;
        seg.reserve(st[s].size() - idx);
        for (int k = idx; k < (int)st[s].size(); ++k) seg.push_back(st[s][k]);
        st[s].resize(idx);
        int dest_start = (int)st[dest].size();
        for (int i = 0; i < (int)seg.size(); ++i) {
            st[dest].push_back(seg[i]);
            pos[seg[i]] = {dest, dest_start + i};
        }
        ops.emplace_back(boxValue, dest + 1);
    };

    auto carry_out = [&](int v) {
        auto [s, idx] = pos[v];
        if (s >= 0 && idx == (int)st[s].size() - 1) {
            st[s].pop_back();
            pos[v] = {-1, -1};
            ops.emplace_back(v, 0);
        } else {
            // Should not happen
        }
    };

    for (int v = 1; v <= n; ++v) {
        auto [s, idx] = pos[v];
        while (idx != (int)st[s].size() - 1) {
            int u = st[s][idx + 1]; // box just above v
            int t = chooseDest(s);
            move_by_box(u, t);
            // v remains at same idx in stack s after moving above segment
            tie(s, idx) = pos[v];
        }
        carry_out(v);
    }

    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }
    return 0;
}