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
    map<int, vector<pair<int, int>>> tile_sq;
    for (int i = 0; i < 50; i++) {
        for (int j = 0; j < 50; j++) {
            tile_sq[t[i][j]].emplace_back(i, j);
        }
    }
    vector<vector<pair<int, int>>> pair_pos(50, vector<pair<int, int>>(50, make_pair(-1, -1)));
    for (auto& entry : tile_sq) {
        auto& sqs = entry.second;
        if (sqs.size() == 2) {
            int i1 = sqs[0].first, j1 = sqs[0].second;
            int i2 = sqs[1].first, j2 = sqs[1].second;
            pair_pos[i1][j1] = {i2, j2};
            pair_pos[i2][j2] = {i1, j1};
        }
    }
    vector<vector<bool>> visited(50, vector<bool>(50, false));
    int ci = si, cj = sj;
    visited[si][sj] = true;
    auto [pi, pj] = pair_pos[si][sj];
    if (pi != -1) {
        visited[pi][pj] = true;
    }
    string path_str = "";
    int dirs[4][2] = {{-1, 0}, {1, 0}, {0, -1}, {0, 1}};
    char move_chars[4] = {'U', 'D', 'L', 'R'};
    while (true) {
        int best_score = -1;
        int best_d = -1;
        int best_ni = -1, best_nj = -1;
        for (int d = 0; d < 4; d++) {
            int ni = ci + dirs[d][0];
            int nj = cj + dirs[d][1];
            if (ni < 0 || ni >= 50 || nj < 0 || nj >= 50 || visited[ni][nj]) continue;
            // temp visit
            visited[ni][nj] = true;
            auto [qi, qj] = pair_pos[ni][nj];
            bool did_block = false;
            if (qi != -1 && !visited[qi][qj]) {
                visited[qi][qj] = true;
                did_block = true;
            }
            // count deg
            int deg = 0;
            for (int dd = 0; dd < 4; dd++) {
                int nni = ni + dirs[dd][0];
                int nnj = nj + dirs[dd][1];
                if (nni >= 0 && nni < 50 && nnj >= 0 && nnj < 50 && !visited[nni][nnj]) deg++;
            }
            // unmark
            visited[ni][nj] = false;
            if (did_block) visited[qi][qj] = false;
            // score
            int score = p[ni][nj] + 25 * deg;
            if (score > best_score) {
                best_score = score;
                best_d = d;
                best_ni = ni;
                best_nj = nj;
            }
        }
        if (best_d == -1) break;
        // go
        path_str += move_chars[best_d];
        // actually visit
        visited[best_ni][best_nj] = true;
        auto [qi, qj] = pair_pos[best_ni][best_nj];
        if (qi != -1 && !visited[qi][qj]) visited[qi][qj] = true;
        ci = best_ni;
        cj = best_nj;
    }
    cout << path_str << endl;
    return 0;
}