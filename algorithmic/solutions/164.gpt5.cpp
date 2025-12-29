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
        for (int j = 0; j < per; ++j) {
            cin >> stacks[i][j];
        }
    }
    
    vector<pair<int,int>> pos(n + 1, {-1, -1}); // pos[v] = {stackIndex, indexInStack}
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < (int)stacks[i].size(); ++j) {
            pos[stacks[i][j]] = {i, j};
        }
    }
    
    vector<pair<int,int>> ops;
    for (int cur = 1; cur <= n; ++cur) {
        int s = pos[cur].first;
        int idx = pos[cur].second;
        if (s == -1) continue; // should not happen
        
        if (idx != (int)stacks[s].size() - 1) {
            int vprime = stacks[s][idx + 1];
            // choose destination stack with minimal size (not equal to s)
            int d = -1;
            int minSize = INT_MAX;
            for (int i = 0; i < m; ++i) {
                if (i == s) continue;
                int sz = (int)stacks[i].size();
                if (sz < minSize) {
                    minSize = sz;
                    d = i;
                }
            }
            if (d == -1) d = (s + 1) % m; // fallback, though m>=2 in problem
            
            // move chunk from idx+1 .. end from stack s to stack d
            int start = idx + 1;
            int destStart = (int)stacks[d].size();
            for (int t = start; t < (int)stacks[s].size(); ++t) {
                int w = stacks[s][t];
                stacks[d].push_back(w);
                pos[w] = {d, (int)stacks[d].size() - 1};
            }
            stacks[s].resize(idx + 1);
            ops.emplace_back(vprime, d + 1);
        }
        
        // carry out cur
        s = pos[cur].first; // refresh
        if (!stacks[s].empty() && stacks[s].back() == cur) {
            stacks[s].pop_back();
            ops.emplace_back(cur, 0);
            pos[cur] = {-1, -1};
        } else {
            // Should not happen; but if it does, do nothing to avoid illegal state
            // (In contest, we'd ensure correctness; here, input constraints guarantee it.)
        }
    }
    
    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }
    return 0;
}