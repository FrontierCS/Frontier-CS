#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    vector<vector<int>> st(m);
    int H = n / m;

    vector<int> where(n + 1, -1), idx(n + 1, -1);
    for (int i = 0; i < m; i++) {
        st[i].resize(H);
        for (int j = 0; j < H; j++) {
            cin >> st[i][j];
            int v = st[i][j];
            where[v] = i;
            idx[v] = j;
        }
    }

    vector<char> removed(n + 1, 0);
    vector<pair<int,int>> ops;
    ops.reserve(5000);

    auto chooseDest = [&](int s) -> int {
        int best = -1;
        int besth = INT_MAX;
        for (int i = 0; i < m; i++) {
            if (i == s) continue;
            int h = (int)st[i].size();
            if (h < besth) {
                besth = h;
                best = i;
            }
        }
        if (best == -1) best = (s + 1) % m; // should never happen for m>=2
        return best;
    };

    auto doMoveByBox = [&](int v, int dest) {
        int s = where[v];
        int start = idx[v];
        if (s == dest) return; // waste (shouldn't happen)

        vector<int> seg;
        seg.reserve(st[s].size() - start);
        for (int i = start; i < (int)st[s].size(); i++) seg.push_back(st[s][i]);
        st[s].resize(start);

        int base = (int)st[dest].size();
        for (int k = 0; k < (int)seg.size(); k++) {
            int x = seg[k];
            st[dest].push_back(x);
            where[x] = dest;
            idx[x] = base + k;
        }
        // boxes remaining in source keep same indices; no update needed
    };

    for (int v = 1; v <= n; v++) {
        if (removed[v]) continue;

        int s = where[v];
        if (s < 0) return 0; // should not happen

        if (!st[s].empty() && st[s].back() == v) {
            ops.emplace_back(v, 0);
            st[s].pop_back();
            removed[v] = 1;
            continue;
        }

        int pos = idx[v];
        if (pos < 0 || pos + 1 >= (int)st[s].size()) return 0; // invalid state

        int u = st[s][pos + 1];
        int dest = chooseDest(s);

        ops.emplace_back(u, dest + 1);
        doMoveByBox(u, dest);

        // now v should be on top of source stack
        if (st[s].empty() || st[s].back() != v) {
            // fallback: keep moving top boxes elsewhere until v reaches top
            while (!st[s].empty() && st[s].back() != v) {
                int t = st[s].back();
                int d2 = chooseDest(s);
                ops.emplace_back(t, d2 + 1);
                doMoveByBox(t, d2);
                if ((int)ops.size() >= 5000) break;
            }
        }

        ops.emplace_back(v, 0);
        if (!st[s].empty() && st[s].back() == v) st[s].pop_back();
        removed[v] = 1;

        if ((int)ops.size() >= 5000) break;
    }

    if ((int)ops.size() > 5000) ops.resize(5000);

    for (auto [a,b] : ops) {
        cout << a << " " << b << "\n";
    }
    return 0;
}