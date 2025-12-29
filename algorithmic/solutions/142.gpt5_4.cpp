#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    int s = n + 1; // spare pole index
    
    vector<vector<int>> st(n + 2); // 1..n+1, bottom->top stored in order, back() is top
    vector<vector<int>> cnt(n + 2, vector<int>(n + 2, 0)); // cnt[pole][color]
    for (int i = 1; i <= n; ++i) {
        st[i].reserve(m);
        for (int j = 0; j < m; ++j) {
            int c; cin >> c;
            st[i].push_back(c);
            cnt[i][c]++;
        }
    }
    st[s].reserve(m);
    
    vector<pair<int,int>> ops;
    ops.reserve(2000000);
    
    auto move_ball = [&](int from, int to) {
        int v = st[from].back();
        st[from].pop_back();
        st[to].push_back(v);
        cnt[from][v]--;
        cnt[to][v]++;
        ops.emplace_back(from, to);
    };
    
    for (int col = 1; col <= n; ++col) {
        int d = col; // destination pole for color 'col'
        for (int i = 1; i <= n; ++i) {
            if (i == d) continue;
            while (cnt[i][col] > 0) {
                // Bring color 'col' to top of pole i
                while (!st[i].empty() && st[i].back() != col) {
                    move_ball(i, s);
                }
                // Now top of i is col (since cnt[i][col] > 0)
                if ((int)st[d].size() == m) {
                    if (st[s].empty()) {
                        // Need to create space in i to accept one from d
                        move_ball(i, s);   // temporarily move the 'col' to spare
                        move_ball(d, i);   // free one slot in d
                        move_ball(s, i);   // bring 'col' back to top of i
                    } else {
                        move_ball(d, i);
                    }
                }
                move_ball(i, d); // move the 'col' to its destination
            }
            // Restore items from spare back to i
            while (!st[s].empty()) {
                move_ball(s, i);
            }
        }
    }
    
    cout << ops.size() << '\n';
    for (auto &p : ops) {
        cout << p.first << ' ' << p.second << '\n';
    }
    return 0;
}