#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<vector<int>> stacks(m);
    int per = n / m;
    for (int i = 0; i < m; ++i) {
        stacks[i].resize(per);
        for (int j = 0; j < per; ++j) cin >> stacks[i][j];
    }

    vector<pair<int,int>> ops;

    auto find_box = [&](int v) -> pair<int,int> {
        for (int i = 0; i < m; ++i) {
            for (int j = 0; j < (int)stacks[i].size(); ++j) {
                if (stacks[i][j] == v) return {i, j};
            }
        }
        return {-1, -1};
    };

    auto top_val = [&](int t) -> int {
        if (stacks[t].empty()) return n + 1;
        return stacks[t].back();
    };

    auto choose_dest = [&](int src, int next_v) -> int {
        vector<int> candidates;
        for (int t = 0; t < m; ++t) {
            if (t == src) continue;
            if (top_val(t) != next_v) candidates.push_back(t);
        }
        if (candidates.empty()) {
            for (int t = 0; t < m; ++t) if (t != src) candidates.push_back(t);
        }
        int best = -1;
        int bestSize = INT_MAX;
        int bestTop = -1;
        for (int t : candidates) {
            int sz = (int)stacks[t].size();
            int tv = top_val(t);
            if (sz < bestSize || (sz == bestSize && tv > bestTop) || (sz == bestSize && tv == bestTop && t < best)) {
                best = t;
                bestSize = sz;
                bestTop = tv;
            }
        }
        if (best == -1) {
            // Fallback (should not happen when m >= 2)
            for (int t = 0; t < m; ++t) if (t != src) { best = t; break; }
        }
        return best;
    };

    for (int v = 1; v <= n; ++v) {
        auto [si, pos] = find_box(v);
        if (si == -1) continue; // should not happen
        int h = (int)stacks[si].size();
        if (pos == h - 1) {
            // v is already at top
            ops.emplace_back(v, 0);
            stacks[si].pop_back();
        } else {
            int dest = choose_dest(si, v + 1);
            int w = stacks[si][pos + 1]; // bottom of the moved block
            // move suffix [pos+1, end) to dest
            vector<int> moved(stacks[si].begin() + pos + 1, stacks[si].end());
            stacks[si].erase(stacks[si].begin() + pos + 1, stacks[si].end());
            stacks[dest].insert(stacks[dest].end(), moved.begin(), moved.end());
            ops.emplace_back(w, dest + 1);
            // now remove v
            ops.emplace_back(v, 0);
            stacks[si].pop_back();
        }
    }

    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }
    return 0;
}