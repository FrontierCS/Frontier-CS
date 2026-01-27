#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<vector<int>> st(m);
    int per = n / m;
    vector<int> posStack(n + 1, -1), posIndex(n + 1, -1);
    for (int i = 0; i < m; ++i) {
        st[i].resize(per);
        for (int j = 0; j < per; ++j) {
            cin >> st[i][j];
            posStack[st[i][j]] = i;
            posIndex[st[i][j]] = j;
        }
    }
    
    vector<pair<int,int>> ops;
    auto move_chunk = [&](int s, int startPos, int dest) {
        if (startPos >= (int)st[s].size()) return;
        vector<int> chunk;
        for (int k = startPos; k < (int)st[s].size(); ++k) chunk.push_back(st[s][k]);
        st[s].resize(startPos);
        int destStart = st[dest].size();
        st[dest].insert(st[dest].end(), chunk.begin(), chunk.end());
        for (int i = 0; i < (int)chunk.size(); ++i) {
            posStack[chunk[i]] = dest;
            posIndex[chunk[i]] = destStart + i;
        }
    };
    
    for (int v = 1; v <= n; ++v) {
        int s = posStack[v];
        int j = posIndex[v];
        if (s == -1) continue;
        if (st[s].back() != v) {
            int u = st[s][j + 1];
            int dest = (s == 0 ? 1 : 0);
            ops.emplace_back(u, dest + 1);
            move_chunk(s, j + 1, dest);
        }
        // Now v should be at top of stack s
        ops.emplace_back(v, 0);
        st[s].pop_back();
        posStack[v] = -1;
        posIndex[v] = -1;
    }
    
    for (auto &op : ops) {
        cout << op.first << " " << op.second << "\n";
    }
    return 0;
}