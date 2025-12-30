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

    vector<int> posStack(n + 1), posIndex(n + 1);
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < (int)st[i].size(); ++j) {
            int v = st[i][j];
            posStack[v] = i;
            posIndex[v] = j;
        }
    }

    vector<pair<int,int>> ops;
    ops.reserve(2 * n + 10);

    for (int cur = 1; cur <= n; ++cur) {
        int s = posStack[cur];
        if (s < 0) continue; // should not happen

        int idx = posIndex[cur];
        if (idx != (int)st[s].size() - 1) {
            int dest = (s + 1) % m;
            int vAbove = st[s][idx + 1];

            ops.emplace_back(vAbove, dest + 1);

            int cut = posIndex[vAbove];
            int len = (int)st[s].size() - cut;
            vector<int> tail;
            tail.reserve(len);
            for (int i = cut; i < (int)st[s].size(); ++i) {
                tail.push_back(st[s][i]);
            }
            st[s].resize(cut);
            for (int val : tail) {
                st[dest].push_back(val);
                posStack[val] = dest;
                posIndex[val] = (int)st[dest].size() - 1;
            }
        }

        s = posStack[cur];
        idx = posIndex[cur];
        ops.emplace_back(cur, 0);
        st[s].pop_back();
        posStack[cur] = -1;
        posIndex[cur] = -1;
    }

    for (auto &p : ops) {
        cout << p.first << ' ' << p.second << '\n';
    }

    return 0;
}