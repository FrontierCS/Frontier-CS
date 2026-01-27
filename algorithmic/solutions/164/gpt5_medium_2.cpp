#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<vector<int>> stacks(m);
    vector<pair<int,int>> pos(n + 1); // pos[v] = {stack_index, index_in_stack}
    int per = n / m;
    for (int i = 0; i < m; ++i) {
        stacks[i].resize(per);
        for (int j = 0; j < per; ++j) {
            int b; cin >> b;
            stacks[i][j] = b;
            pos[b] = {i, j};
        }
    }

    vector<pair<int,int>> ops;

    auto chooseDest = [&](int from)->int{
        int best = -1;
        size_t bestsz = SIZE_MAX;
        for (int i = 0; i < m; ++i) {
            if (i == from) continue;
            if (stacks[i].size() < bestsz) {
                bestsz = stacks[i].size();
                best = i;
            }
        }
        if (best == -1) best = (from + 1) % m;
        return best;
    };

    for (int v = 1; v <= n; ++v) {
        auto [si, pi] = pos[v];
        if (pi != (int)stacks[si].size() - 1) {
            int u = stacks[si][pi + 1];
            int t = chooseDest(si);
            ops.emplace_back(u, t + 1);
            // move segment [pi+1, end) from si to t
            vector<int> seg;
            seg.reserve(stacks[si].size() - (pi + 1));
            for (int idx = pi + 1; idx < (int)stacks[si].size(); ++idx) seg.push_back(stacks[si][idx]);
            stacks[si].resize(pi + 1);
            int start = (int)stacks[t].size();
            stacks[t].insert(stacks[t].end(), seg.begin(), seg.end());
            for (int k = 0; k < (int)seg.size(); ++k) {
                pos[seg[k]] = {t, start + k};
            }
        }
        // now v should be at top of si
        ops.emplace_back(v, 0);
        stacks[si].pop_back();
        pos[v] = {-1, -1};
    }

    // Output
    for (auto &op : ops) {
        cout << op.first << " " << op.second << "\n";
    }
    return 0;
}