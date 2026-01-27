#include <bits/stdc++.h>
using namespace std;

int main() {
    int r, c;
    cin >> r >> c;
    vector<string> grid(r);
    for (int i = 0; i < r; i++) {
        cin >> grid[i];
    }
    vector<pair<int, int>> dirs = {{-1, 0}, {0, 1}, {1, 0}, {0, -1}}; // 0:N, 1:E, 2:S, 3:W
    auto compute_dist = [&](int i, int j, int dir) -> int {
        int dd = 0;
        int di_ = dirs[dir].first;
        int dj_ = dirs[dir].second;
        int ni = i + di_;
        int nj = j + dj_;
        while (ni >= 0 && ni < r && nj >= 0 && nj < c && grid[ni][nj] == '.') {
            dd++;
            ni += di_;
            nj += dj_;
        }
        return dd;
    };
    using tiii = tuple<int, int, int>;
    vector<tiii> possible;
    for (int i = 0; i < r; i++) {
        for (int j = 0; j < c; j++) {
            if (grid[i][j] == '.') {
                for (int d = 0; d < 4; d++) {
                    possible.emplace_back(i, j, d);
                }
            }
        }
    }
    while (true) {
        int dist_in;
        cin >> dist_in;
        if (dist_in == -1) return 0;
        vector<tiii> newp;
        for (auto t : possible) {
            int i, j, ddir;
            tie(i, j, ddir) = t;
            if (compute_dist(i, j, ddir) == dist_in) {
                newp.push_back(t);
            }
        }
        possible = std::move(newp);
        if (possible.empty()) {
            cout << "no" << endl;
            return 0;
        }
        set<pair<int, int>> posset;
        for (auto t : possible) {
            int i, j, dd;
            tie(i, j, dd) = t;
            posset.emplace(i, j);
        }
        if (posset.size() == 1) {
            auto [i, j] = *posset.begin();
            cout << "yes " << i + 1 << " " << j + 1 << endl;
            return 0;
        }
        int cur_num = posset.size();
        auto simulate = [&](char typ) -> int {
            vector<tiii> new_states;
            for (auto t : possible) {
                int i, j, d;
                tie(i, j, d) = t;
                int nd = d;
                int ni = i, nj = j;
                if (typ == 'L') {
                    nd = (d - 1 + 4) % 4;
                } else if (typ == 'R') {
                    nd = (d + 1) % 4;
                } else if (typ == 'S') {
                    nd = d;
                    ni += dirs[d].first;
                    nj += dirs[d].second;
                }
                new_states.emplace_back(ni, nj, nd);
            }
            map<int, set<pair<int, int>>> groups;
            for (auto t : new_states) {
                int pi, pj, pd;
                tie(pi, pj, pd) = t;
                int nextd = compute_dist(pi, pj, pd);
                groups[nextd].emplace(pi, pj);
            }
            int maxr = 0;
            for (auto& p : groups) {
                maxr = max(maxr, (int)p.second.size());
            }
            return maxr;
        };
        int best_score = INT_MAX;
        string best_name;
        char best_type = ' ';
        // left
        int scoreL = simulate('L');
        best_score = scoreL;
        best_name = "left";
        best_type = 'L';
        // right
        int scoreR = simulate('R');
        if (scoreR < best_score) {
            best_score = scoreR;
            best_name = "right";
            best_type = 'R';
        }
        // step if possible
        if (dist_in >= 1) {
            int scoreS = simulate('S');
            if (scoreS < best_score || (scoreS == best_score)) {
                best_score = scoreS;
                best_name = "step";
                best_type = 'S';
            }
        }
        cout << best_name << endl;
        // apply action
        vector<tiii> new_possible;
        for (auto t : possible) {
            int i, j, d;
            tie(i, j, d) = t;
            int nd = d;
            int ni = i, nj = j;
            if (best_type == 'L') {
                nd = (d - 1 + 4) % 4;
            } else if (best_type == 'R') {
                nd = (d + 1) % 4;
            } else if (best_type == 'S') {
                nd = d;
                ni += dirs[d].first;
                nj += dirs[d].second;
            }
            new_possible.emplace_back(ni, nj, nd);
        }
        possible = std::move(new_possible);
    }
    return 0;
}