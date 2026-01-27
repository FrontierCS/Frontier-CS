#include <bits/stdc++.h>
using namespace std;

struct State {
    int x, y, dir;
};

int dx[4] = {-1, 0, 1, 0};
int dy[4] = {0, 1, 0, -1};

int get_dist(int x, int y, int dir, const vector<string>& grid, int r, int c) {
    int cnt = 0;
    int nx = x + dx[dir];
    int ny = y + dy[dir];
    while (nx >= 0 && nx < r && ny >= 0 && ny < c && grid[nx][ny] == '.') {
        cnt++;
        nx += dx[dir];
        ny += dy[dir];
    }
    return cnt;
}

int main() {
    int r, c;
    cin >> r >> c;
    vector<string> grid(r);
    for (int i = 0; i < r; i++) {
        cin >> grid[i];
    }
    vector<State> poss;
    for (int i = 0; i < r; i++) {
        for (int j = 0; j < c; j++) {
            if (grid[i][j] == '.') {
                for (int d = 0; d < 4; d++) {
                    poss.push_back({i, j, d});
                }
            }
        }
    }
    int rounds = 0;
    const int MAX_ROUNDS = 200;
    while (true) {
        int d;
        cin >> d;
        if (d == -1) return 0;
        rounds++;
        if (rounds > MAX_ROUNDS) {
            cout << "no" << endl;
            return 0;
        }
        vector<State> new_poss;
        for (auto s : poss) {
            if (get_dist(s.x, s.y, s.dir, grid, r, c) == d) {
                new_poss.push_back(s);
            }
        }
        poss = new_poss;
        if (poss.empty()) {
            cout << "no" << endl;
            return 0;
        }
        set<pair<int, int>> positions;
        for (auto s : poss) {
            positions.insert({s.x, s.y});
        }
        if (positions.size() == 1) {
            auto [i, j] = *positions.begin();
            cout << "yes " << (i + 1) << " " << (j + 1) << endl;
            return 0;
        }
        // decide best action
        int best_max = INT_MAX;
        string best_action = "";
        bool can_step = true;
        for (auto s : poss) {
            if (get_dist(s.x, s.y, s.dir, grid, r, c) == 0) {
                can_step = false;
                break;
            }
        }
        // try left
        {
            vector<State> post;
            for (auto s : poss) {
                int ndir = (s.dir + 3) % 4;
                post.push_back({s.x, s.y, ndir});
            }
            map<int, int> group_sizes;
            for (auto ps : post) {
                int nd = get_dist(ps.x, ps.y, ps.dir, grid, r, c);
                group_sizes[nd]++;
            }
            int mx = 0;
            for (auto& p : group_sizes) {
                mx = max(mx, p.second);
            }
            if (mx < best_max) {
                best_max = mx;
                best_action = "left";
            }
        }
        // try right
        {
            vector<State> post;
            for (auto s : poss) {
                int ndir = (s.dir + 1) % 4;
                post.push_back({s.x, s.y, ndir});
            }
            map<int, int> group_sizes;
            for (auto ps : post) {
                int nd = get_dist(ps.x, ps.y, ps.dir, grid, r, c);
                group_sizes[nd]++;
            }
            int mx = 0;
            for (auto& p : group_sizes) {
                mx = max(mx, p.second);
            }
            if (mx < best_max) {
                best_max = mx;
                best_action = "right";
            }
        }
        // try step if possible
        if (can_step) {
            vector<State> post;
            for (auto s : poss) {
                int nx = s.x + dx[s.dir];
                int ny = s.y + dy[s.dir];
                post.push_back({nx, ny, s.dir});
            }
            map<int, int> group_sizes;
            for (auto ps : post) {
                int nd = get_dist(ps.x, ps.y, ps.dir, grid, r, c);
                group_sizes[nd]++;
            }
            int mx = 0;
            for (auto& p : group_sizes) {
                mx = max(mx, p.second);
            }
            if (mx < best_max) {
                best_max = mx;
                best_action = "step";
            }
        }
        // if no action splits (best_max == poss.size() and >1 pos), but continue for now
        if (best_action.empty()) {
            // shouldn't happen, at least turns
            best_action = "left";
        }
        cout << best_action << endl;
        // apply action to poss
        vector<State> post;
        if (best_action == "left") {
            for (auto s : poss) {
                int ndir = (s.dir + 3) % 4;
                post.push_back({s.x, s.y, ndir});
            }
        } else if (best_action == "right") {
            for (auto s : poss) {
                int ndir = (s.dir + 1) % 4;
                post.push_back({s.x, s.y, ndir});
            }
        } else { // step
            for (auto s : poss) {
                int nx = s.x + dx[s.dir];
                int ny = s.y + dy[s.dir];
                post.push_back({nx, ny, s.dir});
            }
        }
        poss = post;
    }
    return 0;
}