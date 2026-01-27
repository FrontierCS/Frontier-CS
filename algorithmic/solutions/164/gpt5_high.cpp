#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    int per = n / m;
    
    vector<vector<int>> st(m + 1);
    vector<int> where(n + 1, -1);
    for (int i = 1; i <= m; i++) {
        st[i].reserve(n);
        for (int j = 0; j < per; j++) {
            int x; cin >> x;
            st[i].push_back(x);
            where[x] = i;
        }
    }
    
    vector<pair<int, int>> ops;
    int cur = 1;
    
    auto popFree = [&]() {
        while (cur <= n) {
            int s = where[cur];
            if (s != -1 && !st[s].empty() && st[s].back() == cur) {
                ops.emplace_back(cur, 0);
                st[s].pop_back();
                where[cur] = -1;
                cur++;
            } else break;
        }
    };
    
    auto choose_dest = [&](int sExcl, int y) -> int {
        int best = -1;
        int bestTop = INT_MAX;
        for (int j = 1; j <= m; j++) {
            if (j == sExcl) continue;
            int t = st[j].empty() ? INT_MAX : st[j].back();
            if (t > y && t < bestTop) {
                bestTop = t;
                best = j;
            }
        }
        if (best != -1) return best;
        int best2 = -1;
        int bestTop2 = -1;
        for (int j = 1; j <= m; j++) {
            if (j == sExcl) continue;
            if (st[j].empty()) continue;
            int t = st[j].back();
            if (t <= y && t > bestTop2) {
                bestTop2 = t;
                best2 = j;
            }
        }
        if (best2 != -1) return best2;
        for (int j = 1; j <= m; j++) {
            if (j == sExcl) continue;
            return j;
        }
        return 1;
    };
    
    popFree();
    while (cur <= n) {
        int s = where[cur];
        while (!st[s].empty() && st[s].back() != cur) {
            int y = st[s].back();
            int dest = choose_dest(s, y);
            ops.emplace_back(y, dest);
            st[s].pop_back();
            st[dest].push_back(y);
            where[y] = dest;
            popFree();
        }
        popFree();
    }
    
    for (auto &op : ops) {
        cout << op.first << " " << op.second << "\n";
    }
    return 0;
}