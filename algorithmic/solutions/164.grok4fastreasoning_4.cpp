#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    int sz = n / m;
    vector<vector<int>> stacks(m, vector<int>(sz));
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < sz; j++) {
            cin >> stacks[i][j];
        }
    }
    vector<pair<int, int>> ops;
    int nextv = 1;
    while (nextv <= n) {
        int s = -1;
        for (int i = 0; i < m; i++) {
            if (!stacks[i].empty() && stacks[i].back() == nextv) {
                s = i;
                break;
            }
        }
        if (s != -1) {
            ops.emplace_back(nextv, 0);
            stacks[s].pop_back();
            nextv++;
            continue;
        }
        int src = -1, pos = -1;
        for (int i = 0; i < m; i++) {
            for (size_t j = 0; j < stacks[i].size(); j++) {
                if (stacks[i][j] == nextv) {
                    src = i;
                    pos = j;
                    goto found_pos;
                }
            }
        }
    found_pos:;
        assert(src != -1 && pos != -1);
        int move_v = stacks[src][pos + 1];
        int dest = -1;
        int best_score = INT_MAX;
        for (int t = 0; t < m; t++) {
            if (t == src) continue;
            int h = stacks[t].size();
            bool can = stacks[t].empty() || stacks[t].back() > move_v;
            if (can) {
                int score = h * m + t;
                if (score < best_score) {
                    best_score = score;
                    dest = t;
                }
            }
        }
        if (dest == -1) {
            best_score = INT_MAX;
            for (int t = 0; t < m; t++) {
                if (t == src) continue;
                int h = stacks[t].size();
                int score = h * m + t;
                if (score < best_score) {
                    best_score = score;
                    dest = t;
                }
            }
        }
        assert(dest != -1);
        ops.emplace_back(move_v, dest + 1);
        vector<int> sub(stacks[src].begin() + pos + 1, stacks[src].end());
        stacks[src].erase(stacks[src].begin() + pos + 1, stacks[src].end());
        stacks[dest].insert(stacks[dest].end(), sub.begin(), sub.end());
    }
    for (auto [v, i] : ops) {
        cout << v << " " << i << "\n";
    }
    return 0;
}