#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    int sz = n / m;
    vector<vector<int>> stacks(m);
    for (int i = 0; i < m; i++) {
        stacks[i].resize(sz);
        for (int j = 0; j < sz; j++) {
            cin >> stacks[i][j];
        }
    }
    vector<pair<int, int>> ops;
    for (int cur = 1; cur <= n; cur++) {
        int s = -1, pos = -1;
        bool found = false;
        for (int i = 0; i < m; i++) {
            for (int j = 0; j < (int)stacks[i].size(); j++) {
                if (stacks[i][j] == cur) {
                    s = i;
                    pos = j;
                    found = true;
                    break;
                }
            }
            if (found) break;
        }
        assert(found);
        if (pos == (int)stacks[s].size() - 1) {
            ops.emplace_back(cur, 0);
            stacks[s].pop_back();
        } else {
            int u = stacks[s][pos + 1];
            int best_i = -1;
            int best_top = -1;
            int best_size = 1000;
            for (int i = 0; i < m; i++) {
                if (i == s) continue;
                int thistop = stacks[i].empty() ? 201 : stacks[i].back();
                int thissize = stacks[i].size();
                bool better = false;
                if (thistop > best_top) {
                    better = true;
                } else if (thistop == best_top) {
                    if (thissize < best_size) {
                        better = true;
                    }
                }
                if (better) {
                    best_top = thistop;
                    best_i = i;
                    best_size = thissize;
                }
            }
            assert(best_i != -1);
            int dest = best_i + 1;
            ops.emplace_back(u, dest);
            vector<int> pile;
            for (int j = pos + 1; j < (int)stacks[s].size(); j++) {
                pile.push_back(stacks[s][j]);
            }
            stacks[s].resize(pos + 1);
            for (int x : pile) {
                stacks[best_i].push_back(x);
            }
            assert(stacks[s].back() == cur);
            ops.emplace_back(cur, 0);
            stacks[s].pop_back();
        }
    }
    for (auto [v, i] : ops) {
        cout << v << " " << i << "\n";
    }
    return 0;
}