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
        stacks[i].reserve(n); // enough capacity
        for (int j = 0; j < per; ++j) {
            int x; cin >> x;
            stacks[i].push_back(x);
        }
    }

    auto chooseDest = [&](int s) -> int {
        int dest = -1;
        int bestTop = -1;
        for (int i = 0; i < m; ++i) {
            if (i == s) continue;
            if (stacks[i].empty()) {
                return i;
            } else {
                int top = stacks[i].back();
                if (top > bestTop) {
                    bestTop = top;
                    dest = i;
                }
            }
        }
        if (dest == -1) {
            // Should not happen as m >= 2
            for (int i = 0; i < m; ++i) if (i != s) { dest = i; break; }
        }
        return dest;
    };

    for (int v = 1; v <= n; ++v) {
        int s = -1, idx = -1;
        for (int i = 0; i < m; ++i) {
            for (int j = 0; j < (int)stacks[i].size(); ++j) {
                if (stacks[i][j] == v) {
                    s = i; idx = j; break;
                }
            }
            if (s != -1) break;
        }
        if (s == -1) continue; // safety
        if (idx == (int)stacks[s].size() - 1) {
            cout << v << " " << 0 << "\n";
            stacks[s].pop_back();
        } else {
            int w_idx = idx + 1;
            int w = stacks[s][w_idx];
            int t = chooseDest(s);
            cout << w << " " << (t + 1) << "\n";
            // move tail from s to t
            vector<int> tail;
            tail.reserve(stacks[s].size() - w_idx);
            for (int k = w_idx; k < (int)stacks[s].size(); ++k) tail.push_back(stacks[s][k]);
            stacks[s].erase(stacks[s].begin() + w_idx, stacks[s].end());
            stacks[t].insert(stacks[t].end(), tail.begin(), tail.end());
            // now v is at top of s
            cout << v << " " << 0 << "\n";
            stacks[s].pop_back();
        }
    }

    return 0;
}