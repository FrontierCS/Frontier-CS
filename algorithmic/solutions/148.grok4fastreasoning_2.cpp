#include <bits/stdc++.h>
using namespace std;

int main() {
    int si, sj;
    cin >> si >> sj;
    vector<vector<int>> tile(50, vector<int>(50));
    for (int i = 0; i < 50; i++) {
        for (int j = 0; j < 50; j++) {
            cin >> tile[i][j];
        }
    }
    vector<vector<int>> p(50, vector<int>(50));
    for (int i = 0; i < 50; i++) {
        for (int j = 0; j < 50; j++) {
            cin >> p[i][j];
        }
    }
    vector<vector<bool>> forbidden(50, vector<bool>(50, false));
    int di[4] = {-1, 0, 1, 0};
    int dj[4] = {0, 1, 0, -1};
    int stid = tile[si][sj];
    for (int d = 0; d < 4; d++) {
        int ni = si + di[d];
        int nj = sj + dj[d];
        if (ni >= 0 && ni < 50 && nj >= 0 && nj < 50 && tile[ni][nj] == stid) {
            forbidden[ni][nj] = true;
        }
    }
    // Horizontal dominoes
    for (int i = 0; i < 50; i++) {
        for (int j = 0; j < 49; j++) {
            if (tile[i][j] == tile[i][j + 1]) {
                int i1 = i, j1 = j, i2 = i, j2 = j + 1;
                bool f1 = forbidden[i1][j1], f2 = forbidden[i2][j2];
                if (!f1 && !f2) {
                    if (p[i1][j1] >= p[i2][j2]) {
                        forbidden[i2][j2] = true;
                    } else {
                        forbidden[i1][j1] = true;
                    }
                }
            }
        }
    }
    // Vertical dominoes
    for (int i = 0; i < 49; i++) {
        for (int j = 0; j < 50; j++) {
            if (tile[i][j] == tile[i + 1][j]) {
                int i1 = i, j1 = j, i2 = i + 1, j2 = j;
                bool f1 = forbidden[i1][j1], f2 = forbidden[i2][j2];
                if (!f1 && !f2) {
                    if (p[i1][j1] >= p[i2][j2]) {
                        forbidden[i2][j2] = true;
                    } else {
                        forbidden[i1][j1] = true;
                    }
                }
            }
        }
    }
    // Now build path
    vector<vector<bool>> vis(50, vector<bool>(50, false));
    pair<int, int> curr = {si, sj};
    vis[si][sj] = true;
    string moves = "";
    bool can_move = true;
    while (can_move) {
        can_move = false;
        int min_conn = 5;
        int max_p_for_min = -1;
        pair<int, int> best_next = {-1, -1};
        for (int d = 0; d < 4; d++) {
            int ni = curr.first + di[d];
            int nj = curr.second + dj[d];
            if (ni >= 0 && ni < 50 && nj >= 0 && nj < 50 && !forbidden[ni][nj] && !vis[ni][nj]) {
                int this_conn = 0;
                for (int dd = 0; dd < 4; dd++) {
                    int nni = ni + di[dd];
                    int nnj = nj + dj[dd];
                    if (nni >= 0 && nni < 50 && nnj >= 0 && nnj < 50 && !forbidden[nni][nnj] && !vis[nni][nnj]) {
                        this_conn++;
                    }
                }
                int this_p = p[ni][nj];
                bool better = false;
                if (this_conn < min_conn) {
                    better = true;
                } else if (this_conn == min_conn) {
                    if (this_p > max_p_for_min) {
                        better = true;
                    }
                }
                if (better) {
                    min_conn = this_conn;
                    max_p_for_min = this_p;
                    best_next = {ni, nj};
                }
            }
        }
        if (best_next.first != -1) {
            int deltai = best_next.first - curr.first;
            int deltaj = best_next.second - curr.second;
            char mc;
            if (deltai == -1) mc = 'U';
            else if (deltai == 1) mc = 'D';
            else if (deltaj == -1) mc = 'L';
            else mc = 'R';
            moves += mc;
            curr = best_next;
            vis[curr.first][curr.second] = true;
            can_move = true;
        }
    }
    cout << moves << endl;
    return 0;
}