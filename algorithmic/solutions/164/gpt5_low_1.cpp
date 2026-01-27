#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<vector<int>> st(m);
    int per = n / m;
    vector<pair<int,int>> loc(n+1, {-1,-1}); // (stack, index 0-based)
    for (int i = 0; i < m; ++i) {
        st[i].resize(per);
        for (int j = 0; j < per; ++j) {
            cin >> st[i][j];
            loc[st[i][j]] = {i, j};
        }
    }
    
    vector<pair<int,int>> ops;
    ops.reserve(2*n);
    
    auto move_segment = [&](int u, int to_stack) {
        auto [s, idx] = loc[u];
        if (s == -1) return; // already removed (shouldn't happen)
        if (to_stack == s) {
            // As per statement, allowed but wastes energy; avoid using this.
            // We'll ensure to_stack != s in calls.
        }
        int h = (int)st[s].size();
        int k = h - idx; // number of boxes moved
        // Move st[s][idx..h-1] to st[to_stack]
        int dest_h = (int)st[to_stack].size();
        st[to_stack].reserve(dest_h + k);
        for (int i = idx; i < h; ++i) {
            int box = st[s][i];
            st[to_stack].push_back(box);
            loc[box] = {to_stack, dest_h + (i - idx)};
        }
        st[s].resize(idx);
        // record operation
        ops.emplace_back(u, to_stack+1); // stacks are 1-indexed in output
    };
    
    auto carry_out = [&](int v) {
        auto [s, idx] = loc[v];
        // v must be on top
        // remove top
        st[s].pop_back();
        loc[v] = {-1, -1};
        // update indices of nothing needed since only top removed
        ops.emplace_back(v, 0);
    };
    
    for (int v = 1; v <= n; ++v) {
        auto [s, idx] = loc[v];
        // Ensure v is at top
        if (idx != (int)st[s].size() - 1) {
            // Move the segment above v: start box is st[s][idx+1]
            int u = st[s][idx+1];
            // choose destination stack with minimal height excluding s
            int best_t = -1;
            int best_h = INT_MAX;
            for (int t = 0; t < m; ++t) if (t != s) {
                int h = (int)st[t].size();
                if (h < best_h) {
                    best_h = h;
                    best_t = t;
                }
            }
            if (best_t == -1) best_t = (s+1)%m; // fallback (should not happen)
            move_segment(u, best_t);
            // update s, idx for v after move: now v should be at top in original s
            tie(s, idx) = loc[v];
        }
        // Now v is top
        carry_out(v);
    }
    
    // Output operations
    for (auto &p : ops) {
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}