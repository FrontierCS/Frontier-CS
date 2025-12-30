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
        for (int j = 0; j < h; ++j) {
            cin >> st[i][j];
        }
    }
    
    vector<int> posS(n + 1), posIdx(n + 1);
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < (int)st[i].size(); ++j) {
            int v = st[i][j];
            posS[v] = i;
            posIdx[v] = j;
        }
    }
    
    vector<pair<int,int>> ops;
    
    auto chooseDest = [&](int s)->int {
        int best = -1;
        int bestH = INT_MAX;
        for (int i = 0; i < m; ++i) {
            if (i == s) continue;
            int hh = (int)st[i].size();
            if (hh < bestH) { bestH = hh; best = i; }
        }
        if (best == -1) best = (s + 1) % m;
        return best;
    };
    
    auto moveChunk = [&](int v, int dest) {
        int s = posS[v];
        if (dest == s) {
            dest = chooseDest(s);
            if (dest == s) dest = (s + 1) % m;
        }
        int j = posIdx[v];
        vector<int> moved;
        moved.reserve(st[s].size() - j);
        for (int t = j; t < (int)st[s].size(); ++t) moved.push_back(st[s][t]);
        st[s].resize(j);
        int base = st[dest].size();
        for (int x : moved) {
            st[dest].push_back(x);
        }
        for (int t = 0; t < (int)moved.size(); ++t) {
            int x = moved[t];
            posS[x] = dest;
            posIdx[x] = base + t;
        }
        ops.emplace_back(v, dest + 1);
    };
    
    auto carryOut = [&](int v) {
        int s = posS[v];
        if (!st[s].empty() && st[s].back() == v) {
            st[s].pop_back();
        }
        posS[v] = -1;
        posIdx[v] = -1;
        ops.emplace_back(v, 0);
    };
    
    int nxt = 1;
    while (nxt <= n) {
        int s = posS[nxt];
        if (st[s].back() == nxt) {
            carryOut(nxt);
            ++nxt;
        } else {
            int j = posIdx[nxt];
            int w = st[s][j + 1]; // bottom of the above chunk
            int dest = chooseDest(s);
            moveChunk(w, dest);
        }
    }
    
    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }
    return 0;
}