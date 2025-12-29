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
        stacks[i].reserve(per * 2);
        for (int j = 0; j < per; ++j) {
            int x;
            cin >> x;
            stacks[i].push_back(x); // bottom -> top
        }
    }

    vector<pair<int,int>> ops;
    ops.reserve(2 * n);

    for (int target = 1; target <= n; ++target) {
        int s = -1, idx = -1;
        for (int i = 0; i < m; ++i) {
            auto &st = stacks[i];
            for (int j = 0; j < (int)st.size(); ++j) {
                if (st[j] == target) {
                    s = i;
                    idx = j;
                    break;
                }
            }
            if (s != -1) break;
        }

        if (s == -1) continue; // should not happen

        int h = (int)stacks[s].size();
        if (idx != h - 1) {
            int t = (s + 1) % m;
            if (t == s) t = (s + 1) % m;
            int base = stacks[s][idx + 1]; // box to specify in op1
            ops.push_back({base, t + 1});

            auto &Ss = stacks[s];
            auto &T = stacks[t];
            for (int k = idx + 1; k < h; ++k) {
                T.push_back(Ss[k]);
            }
            Ss.resize(idx + 1);
        }

        // now target is at the top of stack s
        ops.push_back({target, 0});
        stacks[s].pop_back();
    }

    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }

    return 0;
}