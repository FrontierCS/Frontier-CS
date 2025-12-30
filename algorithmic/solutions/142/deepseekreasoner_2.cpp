#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    vector<vector<int>> poles(n + 2); // poles[1..n+1], each vector bottom to top
    vector<vector<int>> cnt(n + 1, vector<int>(n + 2, 0)); // cnt[color][pole]

    for (int i = 1; i <= n; ++i) {
        poles[i].resize(m);
        for (int j = 0; j < m; ++j) {
            cin >> poles[i][j];
            int col = poles[i][j];
            cnt[col][i]++;
        }
    }

    vector<pair<int, int>> moves;

    auto move_ball = [&](int x, int y) {
        int col = poles[x].back();
        poles[x].pop_back();
        poles[y].push_back(col);
        cnt[col][x]--;
        cnt[col][y]++;
        moves.push_back({x, y});
    };

    for (int c = 1; c <= n; ++c) {
        vector<int> allowed;
        for (int i = c + 1; i <= n + 1; ++i) allowed.push_back(i);

        while (cnt[c][c] < m) {
            bool action = false;

            // Condition 1: if pole c has a non-c ball on top, move it out
            if (!poles[c].empty() && poles[c].back() != c) {
                int dest = -1;
                for (int d : allowed) {
                    if (poles[d].size() < m) {
                        dest = d;
                        break;
                    }
                }
                if (dest == -1) {
                    for (int d = 1; d <= n + 1; ++d) {
                        if (d != c && poles[d].size() < m) {
                            dest = d;
                            break;
                        }
                    }
                }
                if (dest != -1) {
                    move_ball(c, dest);
                    action = true;
                }
            }

            if (!action && poles[c].