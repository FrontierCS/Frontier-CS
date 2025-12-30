#include <bits/stdc++.h>
using namespace std;

int main() {
    int si, sj;
    cin >> si >> sj;
    vector<vector<int>> t(50, vector<int>(50));
    int max_tid = 0;
    for (int i = 0; i < 50; i++) {
        for (int j = 0; j < 50; j++) {
            cin >> t[i][j];
            max_tid = max(max_tid, t[i][j]);
        }
    }
    vector<vector<int>> p(50, vector<int>(50));
    for (int i = 0; i < 50; i++) {
        for (int j = 0; j < 50; j++) {
            cin >> p[i][j];
        }
    }
    int M = max_tid + 1;
    vector<vector<pair<int, int>>> tile_squares(M);
    for (int i = 0; i < 50; i++) {
        for (int j = 0; j < 50; j++) {
            tile_squares[t[i][j]].emplace_back(i, j);
        }
    }
    bool visited[50][50];
    memset(visited, 0, sizeof(visited));
    visited[si][sj] = true;
    int ci = si, cj = sj;
    string path = "";
    int dx[4] = {0, 1, 0, -1};
    int dy[4] = {1, 0, -1, 0};
    char dirchar[4] = {'R', 'D', 'L', 'U'};
    while (true) {
        int best_est = -1;
        int best_p = -1;
        int best_d = -1;
        for (int d = 0; d < 4; d++) {
            int ni = ci + dx[d];
            int nj = cj + dy[d];
            if (ni < 0 || ni >= 50 || nj < 0 || nj >= 50) continue;
            if (visited[ni][nj]) continue;
            int tid_n = t[ni][nj];
            int tid_c = t[ci][cj];
            bool same_tile = (tid_n == tid_c);
            bool tile_free = true;
            if (!same_tile) {
                auto& sqs = tile_squares[tid_n];
                for (auto [x, y] : sqs) {
                    if (visited[x][y]) {
                        tile_free = false;
                        break;
                    }
                }
                if (!tile_free) continue;
            }
            // temp mark
            visited[ni][nj] = true;
            // rem_current
            int rem_current = 0;
            auto& sqs_c = tile_squares[tid_n];
            for (auto [x, y] : sqs_c) {
                if (!visited[x][y]) rem_current += p[x][y];
            }
            // free_s
            int free_s = 0;
            for (int tt = 0; tt < M; tt++) {
                if (tt == tid_n) continue;
                auto& sqs = tile_squares[tt];
                bool any_v = false;
                int s_tile = 0;
                for (auto [x, y] : sqs) {
                    s_tile += p[x][y];
                    if (visited[x][y]) any_v = true;
                }
                if (!any_v) free_s += s_tile;
            }
            int est = p[ni][nj] + rem_current + free_s;
            // unmark
            visited[ni][nj] = false;
            int this_p = p[ni][nj];
            bool better = false;
            if (est > best_est) {
                better = true;
            } else if (est == best_est) {
                if (this_p > best_p) {
                    better = true;
                } else if (this_p == best_p && d < best_d) {
                    better = true;
                }
            }
            if (better) {
                best_est = est;
                best_p = this_p;
                best_d = d;
            }
        }
        if (best_d == -1) break;
        int ni = ci + dx[best_d];
        int nj = cj + dy[best_d];
        visited[ni][nj] = true;
        path += dirchar[best_d];
        ci = ni;
        cj = nj;
    }
    cout << path << endl;
    return 0;
}