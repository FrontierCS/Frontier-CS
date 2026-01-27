#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int r, c;
    cin >> r >> c;
    vector<string> grid(r);
    for (int i = 0; i < r; i++) {
        cin >> grid[i];
    }
    int drs[4][2] = {{-1, 0}, {0, 1}, {1, 0}, {0, -1}};
    vector<vector<vector<int>>> Dist(r, vector<vector<int>>(c, vector<int>(4, 0)));
    for (int i = 0; i < r; i++) {
        for (int j = 0; j < c; j++) {
            if (grid[i][j] != '.') continue;
            for (int d = 0; d < 4; d++) {
                int di = drs[d][0], dj = drs[d][1];
                int cnt = 0;
                int ni = i + di, nj = j + dj;
                while (ni >= 0 && ni < r && nj >= 0 && nj < c && grid[ni][nj] == '.') {
                    cnt++;
                    ni += di;
                    nj += dj;
                }
                Dist[i][j][d] = cnt;
            }
        }
    }
    vector<tuple<int, int, int>> possible;
    for (int i = 0; i < r; i++) {
        for (int j = 0; j < c; j++) {
            if (grid[i][j] == '.') {
                for (int d = 0; d < 4; d++) {
                    possible.emplace_back(i, j, d);
                }
            }
        }
    }
    const int MAXP = 100 * 100 + 10;
    auto get_pos_count = [&](const vector<tuple<int, int, int>>& states) -> int {
        bitset<MAXP> bs;
        for (auto [i, j, _] : states) {
            bs[i * c + j] = 1;
        }
        return bs.count();
    };
    vector<string> action_names = {"left", "right", "step"};
    while (true) {
        int d;
        cin >> d;
        if (d == -1) return 0;
        vector<tuple<int, int, int>> new_pos;
        for (auto st : possible) {
            auto [i, j, dd] = st;
            if (Dist[i][j][dd] == d) {
                new_pos.push_back(st);
            }
        }
        possible = std::move(new_pos);
        int curr_count = get_pos_count(possible);
        if (curr_count == 0) {
            cout << "no" << endl;
            return 0;
        }
        if (curr_count == 1) {
            auto [i, j, _] = possible[0];
            cout << "yes " << (i + 1) << " " << (j + 1) << endl;
            return 0;
        }
        bool can_step = true;
        for (auto st : possible) {
            auto [i, j, dd] = st;
            int di = drs[dd][0], dj = drs[dd][1];
            int ni = i + di, nj = j + dj;
            if (ni < 0 || ni >= r || nj < 0 || nj >= c || grid[ni][nj] != '.') {
                can_step = false;
                break;
            }
        }
        int best_action = -1;
        int best_worst = INT_MAX;
        for (int act = 0; act < 3; act++) {
            if (act == 2 && !can_step) continue;
            vector<bitset<MAXP>> branches(100);
            for (auto st : possible) {
                auto [i, j, dd] = st;
                int newi = i, newj = j, newdd = dd;
                if (act == 0) {
                    newdd = (dd + 3) % 4;
                } else if (act == 1) {
                    newdd = (dd + 1) % 4;
                } else {
                    int di = drs[dd][0], dj = drs[dd][1];
                    newi += di;
                    newj += dj;
                }
                int nextd = Dist[newi][newj][newdd];
                int posid = newi * c + newj;
                branches[nextd][posid] = 1;
            }
            int worst = 0;
            for (int dd = 0; dd < 100; dd++) {
                if (branches[dd].any()) {
                    worst = max(worst, (int)branches[dd].count());
                }
            }
            if (worst < best_worst) {
                best_worst = worst;
                best_action = act;
            }
        }
        if (best_worst == curr_count) {
            cout << "no" << endl;
            return 0;
        }
        string act_str = action_names[best_action];
        cout << act_str << endl;
        vector<tuple<int, int, int>> updated;
        for (auto st : possible) {
            auto [i, j, dd] = st;
            int newi = i, newj = j, newdd = dd;
            if (best_action == 0) {
                newdd = (dd + 3) % 4;
            } else if (best_action == 1) {
                newdd = (dd + 1) % 4;
            } else {
                int di = drs[dd][0], dj = drs[dd][1];
                newi += di;
                newj += dj;
            }
            updated.emplace_back(newi, newj, newdd);
        }
        possible = std::move(updated);
    }
    return 0;
}