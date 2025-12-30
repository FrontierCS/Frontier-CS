#include <bits/stdc++.h>
using namespace std;

int main() {
    int si, sj;
    cin >> si >> sj;
    vector<vector<int>> t(50, vector<int>(50));
    for (int i = 0; i < 50; i++) {
        for (int j = 0; j < 50; j++) {
            cin >> t[i][j];
        }
    }
    vector<vector<int>> p(50, vector<int>(50));
    for (int i = 0; i < 50; i++) {
        for (int j = 0; j < 50; j++) {
            cin >> p[i][j];
        }
    }
    int M = 0;
    for (int i = 0; i < 50; i++) {
        for (int j = 0; j < 50; j++) {
            M = max(M, t[i][j]);
        }
    }
    M++;
    vector<vector<pair<int, int>>> tiles(M);
    for (int i = 0; i < 50; i++) {
        for (int j = 0; j < 50; j++) {
            tiles[t[i][j]].emplace_back(i, j);
        }
    }
    vector<long long> tile_sum(M, 0);
    for (int id = 0; id < M; id++) {
        for (auto [x, y] : tiles[id]) {
            tile_sum[id] += p[x][y];
        }
    }
    auto complete_tile = [&](auto&& self, int ti, int tj, int& ci, int& cj, string& path_str) -> void {
        int id = t[ti][tj];
        auto& sq = tiles[id];
        if (sq.size() == 1) return;
        pair<int, int> other;
        for (auto pr : sq) {
            if (pr.first != ti || pr.second != tj) {
                other = pr;
                break;
            }
        }
        int di = other.first - ti;
        int dj = other.second - tj;
        char move;
        if (di == -1) move = 'U';
        else if (di == 1) move = 'D';
        else if (dj == -1) move = 'L';
        else if (dj == 1) move = 'R';
        else assert(false);
        path_str += move;
        ci = other.first;
        cj = other.second;
    };
    string path_str = "";
    int ci = si, cj = sj;
    int current_tile = t[si][sj];
    complete_tile(complete_tile, si, sj, ci, cj, path_str);
    current_tile = t[ci][cj];
    set<int> finished;
    int dx[4] = {-1, 1, 0, 0};
    int dy[4] = {0, 0, -1, 1};
    char dirs[4] = {'U', 'D', 'L', 'R'};
    auto get_remaining = [&](int id, const set<int>& fin) -> int {
        set<int> adj;
        for (auto [x, y] : tiles[id]) {
            for (int dd = 0; dd < 4; dd++) {
                int nx = x + dx[dd];
                int ny = y + dy[dd];
                if (nx >= 0 && nx < 50 && ny >= 0 && ny < 50) {
                    int tid = t[nx][ny];
                    if (tid != id && fin.find(tid) == fin.end()) {
                        adj.insert(tid);
                    }
                }
            }
        }
        return adj.size();
    };
    while (true) {
        vector<tuple<int, long long, int, int, int>> candidates;
        for (int d = 0; d < 4; d++) {
            int ni = ci + dx[d];
            int nj = cj + dy[d];
            if (ni < 0 || ni >= 50 || nj < 0 || nj >= 50) continue;
            int nid = t[ni][nj];
            if (finished.count(nid) || nid == current_tile) continue;
            int rem = get_remaining(nid, finished);
            candidates.emplace_back(rem, -tile_sum[nid], d, ni, nj);
        }
        if (candidates.empty()) break;
        sort(candidates.begin(), candidates.end());
        auto [rem, negsum, best_d, best_ni, best_nj] = candidates[0];
        char move = dirs[best_d];
        path_str += move;
        finished.insert(current_tile);
        ci = best_ni;
        cj = best_nj;
        int new_tile = t[ci][cj];
        complete_tile(complete_tile, ci, cj, ci, cj, path_str);
        current_tile = t[ci][cj];
    }
    cout << path_str << endl;
}