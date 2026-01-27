#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    
    int E; // index of empty pole
    E = n + 1;
    
    vector<vector<int>> poles(n + 2);
    vector<vector<int>> cnt(n + 2, vector<int>(n + 2, 0));
    
    for (int i = 1; i <= n; ++i) {
        poles[i].reserve(m);
        for (int j = 0; j < m; ++j) {
            int c; cin >> c;
            poles[i].push_back(c);
            cnt[i][c]++;
        }
    }
    // E is initially empty
    vector<pair<int,int>> ops;
    ops.reserve(2000005);
    
    auto move_ball = [&](int x, int y) {
        int color = poles[x].back();
        poles[x].pop_back();
        poles[y].push_back(color);
        cnt[x][color]--;
        cnt[y][color]++;
        ops.emplace_back(x, y);
    };
    
    for (int c = 1; c <= n; ++c) {
        int dest = c; // assign color c to pole c
        for (int j = 1; j <= n; ++j) {
            if (j == dest) continue;
            while (cnt[j][c] > 0) {
                while (!poles[j].empty() && poles[j].back() != c) {
                    move_ball(j, E);
                }
                // Now top of j is color c
                move_ball(dest, E);
                move_ball(j, dest);
                move_ball(E, j);
            }
            // Return remaining from E back to j
            while (!poles[E].empty()) {
                move_ball(E, j);
            }
        }
    }
    
    cout << ops.size() << '\n';
    for (auto &p : ops) {
        cout << p.first << ' ' << p.second << '\n';
    }
    return 0;
}