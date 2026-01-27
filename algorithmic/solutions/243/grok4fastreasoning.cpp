#include <bits/stdc++.h>
using namespace std;

struct State {
    int x, y, dir;
};

int main() {
    int r, c;
    cin >> r >> c;
    vector<string> grid(r);
    for (int i = 0; i < r; i++) {
        cin >> grid[i];
    }
    vector<State> curr_possible;
    for (int i = 0; i < r; i++) {
        for (int j = 0; j < c; j++) {
            if (grid[i][j] == '.') {
                for (int d = 0; d < 4; d++) {
                    curr_possible.push_back({i, j, d});
                }
            }
        }
    }
    int DX[4] = {-1, 0, 1, 0};
    int DY[4] = {0, 1, 0, -1};
    auto calc_dist = [&](int x, int y, int dir) -> int {
        int cnt = 0;
        int cx = x + DX[dir];
        int cy = y + DY[dir];
        while (cx >= 0 && cx < r && cy >= 0 && cy < c && grid[cx][cy] == '.') {
            cnt++;
            cx += DX[dir];
            cy += DY[dir];
        }
        return cnt;
    };
    int actions_taken = 0;
    while (true) {
        int d;
        cin >> d;
        if (d == -1) return 0;
        vector<State> filtered;
        for (auto s : curr_possible) {
            if (calc_dist(s.x, s.y, s.dir) == d) {
                filtered.push_back(s);
            }
        }
        curr_possible = filtered;
        if (curr_possible.empty()) {
            cout << "no" << endl;
            return 0;
        }
        set<pair<int, int>> curr_pos_set;
        for (auto& s : curr_possible) {
            curr_pos_set.insert({s.x, s.y});
        }
        if (curr_pos_set.size() == 1) {
            auto [ix, iy] = *curr_pos_set.begin();
            cout << "yes " << ix + 1 << " " << iy + 1 << endl;
            return 0;
        }
        bool can_step = true;
        for (auto& s : curr_possible) {
            int nx = s.x + DX[s.dir];
            int ny = s.y + DY[s.dir];
            if (nx < 0 || nx >= r || ny < 0 || ny >= c || grid[nx][ny] != '.') {
                can_step = false;
                break;
            }
        }
        int max_l = 0;
        {
            vector<set<pair<int, int>>> groups(100);
            for (auto& s : curr_possible) {
                int ndir = (s.dir + 3) % 4;
                int dp = calc_dist(s.x, s.y, ndir);
                groups[dp].insert({s.x, s.y});
            }
            for (auto& g : groups) {
                if (!g.empty()) {
                    max_l = max(max_l, (int)g.size());
                }
            }
        }
        int max_r = 0;
        {
            vector<set<pair<int, int>>> groups(100);
            for (auto& s : curr_possible) {
                int ndir = (s.dir + 1) % 4;
                int dp = calc_dist(s.x, s.y, ndir);
                groups[dp].insert({s.x, s.y});
            }
            for (auto& g : groups) {
                if (!g.empty()) {
                    max_r = max(max_r, (int)g.size());
                }
            }
        }
        int max_s = INT_MAX;
        if (can_step) {
            max_s = 0;
            vector<set<pair<int, int>>> groups(100);
            for (auto& s : curr_possible) {
                int nx = s.x + DX[s.dir];
                int ny = s.y + DY[s.dir];
                int ndir = s.dir;
                int dp = calc_dist(nx, ny, ndir);
                groups[dp].insert({nx, ny});
            }
            for (auto& g : groups) {
                if (!g.empty()) {
                    max_s = max(max_s, (int)g.size());
                }
            }
        }
        int min_max = min({max_l, max_r, can_step ? max_s : INT_MAX});
        int chosen = -1;
        if (can_step && max_s == min_max) {
            chosen = 2;
        } else if (max_l == min_max) {
            chosen = 0;
        } else {
            chosen = 1;
        }
        string cmd;
        if (chosen == 0) {
            cmd = "left";
        } else if (chosen == 1) {
            cmd = "right";
        } else {
            cmd = "step";
        }
        cout << cmd << endl;
        actions_taken++;
        if (actions_taken > 500) {
            cout << "no" << endl;
            return 0;
        }
        vector<State> new_possible;
        for (auto& s : curr_possible) {
            int nx = s.x;
            int ny = s.y;
            int nd = s.dir;
            if (chosen == 0) {
                nd = (nd + 3) % 4;
            } else if (chosen == 1) {
                nd = (nd + 1) % 4;
            } else {
                nx += DX[nd];
                ny += DY[nd];
            }
            new_possible.push_back({nx, ny, nd});
        }
        curr_possible = new_possible;
    }
    return 0;
}