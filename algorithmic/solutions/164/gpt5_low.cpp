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
    // position map: pos[v] = {stack_index (0-based), index_in_stack (0-based from bottom)}
    vector<pair<int,int>> pos(n+1, {-1,-1});
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < (int)stacks[i].size(); ++j) {
            pos[stacks[i][j]] = {i, j};
        }
    }

    vector<pair<int,int>> ops;

    auto choose_dest = [&](int s)->int{
        int best = -1, bestsz = INT_MAX;
        for (int i = 0; i < m; ++i) if (i != s) {
            int sz = (int)stacks[i].size();
            if (sz < bestsz) { bestsz = sz; best = i; }
        }
        if (best == -1) best = (s+1 < m ? s+1 : 0); // fallback (shouldn't happen when m>=2)
        if (best == s) best = (s+1)%m;
        return best;
    };

    for (int cur = 1; cur <= n; ++cur) {
        auto [s, j] = pos[cur];
        if (s == -1) continue; // already carried (shouldn't happen)
        int h = (int)stacks[s].size();
        if (j != h-1) {
            int v = stacks[s][j+1];
            int t = choose_dest(s);
            // move chunk [j+1, h)
            vector<int> moving;
            moving.reserve(h - (j+1));
            for (int idx = j+1; idx < h; ++idx) moving.push_back(stacks[s][idx]);
            stacks[s].erase(stacks[s].begin()+j+1, stacks[s].end());
            for (int x : moving) {
                pos[x] = {t, (int)stacks[t].size()};
                stacks[t].push_back(x);
            }
            ops.emplace_back(v, t+1);
            // cur now at top of s; j remains its index
        }
        // carry out cur
        stacks[s].pop_back();
        pos[cur] = {-1,-1};
        ops.emplace_back(cur, 0);
    }

    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }
    return 0;
}